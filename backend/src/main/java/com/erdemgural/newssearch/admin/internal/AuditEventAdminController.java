package com.erdemgural.newssearch.admin.internal;

import com.erdemgural.newssearch.audit.AuditAction;
import com.erdemgural.newssearch.audit.AuditEvent;
import com.erdemgural.newssearch.audit.AuditEventFilter;
import com.erdemgural.newssearch.audit.AuditLog;
import com.erdemgural.newssearch.audit.AuditRecord;
import com.erdemgural.newssearch.audit.AuditTargetType;
import com.erdemgural.newssearch.audit.AuditTrail;
import com.erdemgural.newssearch.identity.CurrentUser;
import com.erdemgural.newssearch.identity.UserAdministration;
import com.erdemgural.newssearch.web.ApiException;
import com.erdemgural.newssearch.web.ErrorCode;
import com.erdemgural.newssearch.web.FieldError;
import com.erdemgural.newssearch.web.FieldError.Code;
import com.erdemgural.newssearch.web.InvalidRequestException;
import com.erdemgural.newssearch.web.PageParameters;
import com.erdemgural.newssearch.web.PageResponse;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.io.PrintWriter;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import tools.jackson.databind.json.JsonMapper;

/**
 * Audit kayıtlarının listesi ve CSV dışa aktarma (API sözleşmesi 6.8; FG-YP-10, FG-YP-11). Yalnızca
 * {@code ADMIN} rolüne açıktır ({@code /api/v1/admin/**}, güvenlik ayarı).
 *
 * <p>Kayıtlarda kullanıcı kimliği vardır; e-postası {@code identity} modülünden toplu olarak alınır.
 */
@RestController
@RequestMapping("/api/v1/admin/audit-events")
class AuditEventAdminController {

    /** Dışa aktarılabilecek en fazla kayıt (sözleşme 6.8). */
    static final int MAX_EXPORT_ROWS = 100_000;

    /** Tarih aralığı verilmezse son 30 gün (sözleşme 6.8). */
    private static final Duration DEFAULT_RANGE = Duration.ofDays(30);

    /** İşlem kodunun biçimi; sabit bir listeyle karşılaştırılmaz, çünkü işçinin kodları da aranır. */
    private static final Pattern ACTION = Pattern.compile("[A-Z][A-Z_]{0,63}");

    private static final List<String> RESULTS = List.of("SUCCESS", "FAILURE");

    private static final Set<String> TARGET_TYPES =
            Arrays.stream(AuditTargetType.values()).map(Enum::name).collect(Collectors.toUnmodifiableSet());

    private static final DateTimeFormatter FILE_TIME =
            DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss").withZone(ZoneOffset.UTC);

    /**
     * Adres parametreleri; Spring aynı adlı parametreleri bu kaydın alanlarına doldurur. Metin olarak
     * alınırlar: geçersiz olanların hepsi alan adı ve koduyla birlikte bildirilir (sözleşme 2.6).
     */
    record AuditEventQuery(
            String actorUserId,
            String action,
            String targetType,
            String targetId,
            String result,
            String from,
            String to) {}

    private final AuditTrail auditTrail;
    private final AuditLog auditLog;
    private final UserAdministration userAdministration;
    private final JsonMapper jsonMapper;
    private final Clock clock;

    AuditEventAdminController(
            AuditTrail auditTrail,
            AuditLog auditLog,
            UserAdministration userAdministration,
            JsonMapper jsonMapper,
            Clock clock) {
        this.auditTrail = auditTrail;
        this.auditLog = auditLog;
        this.userAdministration = userAdministration;
        this.jsonMapper = jsonMapper;
        this.clock = clock;
    }

    @GetMapping
    PageResponse<AuditEventResponse> list(
            AuditEventQuery query,
            @RequestParam(required = false) String page,
            @RequestParam(required = false) String size) {
        List<FieldError> errors = new ArrayList<>();
        AuditEventFilter filter = toFilter(query, clock.instant(), errors);
        PageParameters pageParameters = PageParameters.parse(page, size, errors);
        if (!errors.isEmpty()) {
            throw new InvalidRequestException(errors);
        }
        PageResponse<AuditRecord> records = auditTrail.list(filter, pageParameters);
        Map<UUID, String> emails = emailsOf(records.items());
        return records.map(record -> AuditEventResponse.from(record, emails));
    }

    /**
     * Filtreye uyan kayıtları CSV dosyası olarak yazar. Önce sayılır; sınır aşılırsa dosya hiç başlamaz.
     * Dışa aktarmanın kendisi de audit'e yazılır (FG-AL-01); sınırı aşan istek bir doğrulama hatasıdır ve
     * yazılmaz.
     */
    @GetMapping("/export")
    void export(@AuthenticationPrincipal CurrentUser admin, AuditEventQuery query, HttpServletResponse response)
            throws IOException {
        List<FieldError> errors = new ArrayList<>();
        Instant now = clock.instant();
        AuditEventFilter requested = toFilter(query, now, errors);
        if (!errors.isEmpty()) {
            throw new InvalidRequestException(errors);
        }
        // Üst sınır dışa aktarmanın başladığı ana sabitlenir: sayım ile dosya aynı kayıtları kapsar ve bu
        Instant to = requested.to().isAfter(now) ? now : requested.to();
        AuditEventFilter filter = new AuditEventFilter(
                requested.actorUserId(),
                requested.action(),
                requested.targetType(),
                requested.targetId(),
                requested.result(),
                requested.from(),
                to);

        long rowCount = auditTrail.count(filter);
        if (rowCount > MAX_EXPORT_ROWS) {
            throw new ApiException(HttpStatus.BAD_REQUEST, ErrorCode.EXPORT_TOO_LARGE);
        }
        auditLog.record(AuditEvent.success(
                admin.id(), AuditAction.AUDIT_EXPORTED, null, null, exportDetails(filter, rowCount)));

        response.setContentType("text/csv;charset=UTF-8");
        response.setHeader(
                HttpHeaders.CONTENT_DISPOSITION,
                ContentDisposition.attachment()
                        .filename("audit-events-" + FILE_TIME.format(now) + ".csv")
                        .build()
                        .toString());
        PrintWriter writer = response.getWriter();
        writer.write(AuditCsv.BOM);
        writer.write(AuditCsv.line(AuditCsv.HEADER));
        auditTrail.forEachChunk(filter, chunk -> {
            Map<UUID, String> emails = emailsOf(chunk);
            for (AuditRecord record : chunk) {
                writer.write(AuditCsv.line(csvValues(record, emails)));
            }
        });
        writer.flush();
    }

    /** Kayıtlardaki kullanıcıların e-postaları, tek sorguyla. */
    private Map<UUID, String> emailsOf(List<AuditRecord> records) {
        Set<UUID> userIds = records.stream()
                .map(AuditRecord::actorUserId)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());
        return userAdministration.findEmails(userIds);
    }

    /** Başlıktaki sütunların sırasıyla. Zaman ISO 8601 ve UTC (sözleşme 2.3). */
    private String[] csvValues(AuditRecord record, Map<UUID, String> emails) {
        return new String[] {
            record.id().toString(),
            record.occurredAt().toString(),
            record.actorType(),
            Objects.toString(record.actorUserId(), null),
            record.actorUserId() == null ? null : emails.get(record.actorUserId()),
            record.action(),
            record.targetType(),
            Objects.toString(record.targetId(), null),
            record.result(),
            record.requestId(),
            record.ipAddress(),
            record.details().isEmpty() ? null : jsonMapper.writeValueAsString(record.details())
        };
    }

    /** Dışa aktarma kaydının ayrıntısı: kullanılan filtreler ve kayıt sayısı. */
    private static Map<String, Object> exportDetails(AuditEventFilter filter, long rowCount) {
        Map<String, Object> details = new HashMap<>();
        putIfPresent(details, "actorUserId", filter.actorUserId());
        putIfPresent(details, "action", filter.action());
        putIfPresent(details, "targetType", filter.targetType());
        putIfPresent(details, "targetId", filter.targetId());
        putIfPresent(details, "result", filter.result());
        details.put("from", filter.from().toString());
        details.put("to", filter.to().toString());
        details.put("rowCount", rowCount);
        return details;
    }

    private static void putIfPresent(Map<String, Object> details, String key, Object value) {
        if (value != null) {
            details.put(key, value.toString());
        }
    }

    /**
     * Parametreleri okur ve doğrular; hatalar {@code errors} listesine eklenir. Tarih aralığı verilmezse son
     * 30 gün; yalnızca üst sınır verilirse ondan önceki 30 gün.
     */
    private static AuditEventFilter toFilter(AuditEventQuery query, Instant now, List<FieldError> errors) {
        UUID actorUserId = parseUuid("actorUserId", query.actorUserId(), errors);
        String action = blankToNull(query.action());
        if (action != null && !ACTION.matcher(action).matches()) {
            errors.add(new FieldError("action", Code.INVALID_VALUE));
        }
        String targetType = blankToNull(query.targetType());
        if (targetType != null && !TARGET_TYPES.contains(targetType)) {
            errors.add(new FieldError("targetType", Code.INVALID_VALUE));
        }
        UUID targetId = parseUuid("targetId", query.targetId(), errors);
        String result = blankToNull(query.result());
        if (result != null && !RESULTS.contains(result)) {
            errors.add(new FieldError("result", Code.INVALID_VALUE));
        }
        Instant from = parseInstant("from", query.from(), errors);
        Instant to = parseInstant("to", query.to(), errors);
        if (from != null && to != null && from.isAfter(to)) {
            errors.add(new FieldError("from", Code.INVALID_RANGE));
        }
        // Üst sınır verilmezse şimdi: veritabanı ancak iki sınır da belliyse aralık dışındaki bölümleri atlar.
        Instant upperBound = to != null ? to : now;
        Instant lowerBound = from != null ? from : upperBound.minus(DEFAULT_RANGE);
        return new AuditEventFilter(actorUserId, action, targetType, targetId, result, lowerBound, upperBound);
    }

    private static String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.strip();
    }

    private static UUID parseUuid(String field, String value, List<FieldError> errors) {
        String text = blankToNull(value);
        if (text == null) {
            return null;
        }
        try {
            return UUID.fromString(text);
        } catch (IllegalArgumentException exception) {
            errors.add(new FieldError(field, Code.INVALID_VALUE));
            return null;
        }
    }

    /** ISO 8601 ve UTC (sözleşme 2.3): {@code 2026-11-05T09:30:00Z}. */
    private static Instant parseInstant(String field, String value, List<FieldError> errors) {
        String text = blankToNull(value);
        if (text == null) {
            return null;
        }
        try {
            return Instant.parse(text);
        } catch (DateTimeParseException exception) {
            errors.add(new FieldError(field, Code.INVALID_VALUE));
            return null;
        }
    }
}
