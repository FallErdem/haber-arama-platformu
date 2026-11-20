package com.erdemgural.newssearch.ingestion.internal;

import com.erdemgural.newssearch.audit.AuditAction;
import com.erdemgural.newssearch.audit.AuditEvent;
import com.erdemgural.newssearch.audit.AuditLog;
import com.erdemgural.newssearch.audit.AuditTargetType;
import com.erdemgural.newssearch.ingestion.FeedChange;
import com.erdemgural.newssearch.ingestion.ManagedFeed;
import com.erdemgural.newssearch.ingestion.ManagedSource;
import com.erdemgural.newssearch.ingestion.NewFeed;
import com.erdemgural.newssearch.ingestion.NewSource;
import com.erdemgural.newssearch.ingestion.SourceAdministration;
import com.erdemgural.newssearch.ingestion.SourceChange;
import com.erdemgural.newssearch.ingestion.SourceOverview;
import com.erdemgural.newssearch.ingestion.internal.ManagedFeedRepository.FeedSettings;
import com.erdemgural.newssearch.ingestion.internal.ManagedSourceRepository.SourceSettings;
import com.erdemgural.newssearch.web.ApiException;
import com.erdemgural.newssearch.web.ErrorCode;
import com.erdemgural.newssearch.web.FieldError;
import com.erdemgural.newssearch.web.InvalidRequestException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;
import java.util.function.Supplier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * {@link SourceAdministration}'ın uygulaması: kaynak ve besleme ekleme, düzenleme, etkinleştirme ve devre dışı
 * bırakma, elle toplama; iyimser kilitleme ve audit kayıtları.
 *
 * <p>Kullanıcı yönetimindeki kural burada da geçerlidir: her değişiklik ve audit kaydı tek veritabanı
 * işleminde yazılır; kural ihlalinde (409) işlem geri alınır ve denemenin {@code FAILURE} kaydı işlem
 * bittikten sonra ayrıca yazılır. Bu yüzden işlem {@link TransactionTemplate} ile açılır.
 */
@Service
class SourceAdministrationService implements SourceAdministration {

    private static final Logger log = LoggerFactory.getLogger(SourceAdministrationService.class);

    private static final String AUTO = "AUTO";
    private static final String MANUAL = "MANUAL";

    /** Denenen bir işlem: başarısız olursa hangi kodla, hangi nesne için ve hangi ayrıntıyla yazılacağı. */
    private record Attempt(
            AuditAction action, AuditTargetType targetType, UUID targetId, Map<String, Object> details) {}

    private final ManagedSourceRepository sources;
    private final ManagedFeedRepository feeds;
    private final AuditLog auditLog;
    private final TransactionTemplate transactionTemplate;

    SourceAdministrationService(
            ManagedSourceRepository sources,
            ManagedFeedRepository feeds,
            AuditLog auditLog,
            TransactionTemplate transactionTemplate) {
        this.sources = sources;
        this.feeds = feeds;
        this.auditLog = auditLog;
        this.transactionTemplate = transactionTemplate;
    }

    @Override
    public List<SourceOverview> listSources() {
        return sources.findOverviews();
    }

    @Override
    public ManagedSource findSource(UUID sourceId) {
        ManagedSource source = sources.findById(sourceId).orElseThrow(SourceAdministrationService::notFound);
        return withFeeds(source);
    }

    @Override
    public ManagedSource createSource(UUID adminId, NewSource source) {
        Attempt attempt = new Attempt(AuditAction.SOURCE_CREATED, null, null, Map.of("code", source.code()));
        UUID sourceId = audited(adminId, List.of(attempt), () -> {
            UUID created = sources.insert(source);
            recordSuccess(
                    adminId,
                    AuditAction.SOURCE_CREATED,
                    AuditTargetType.SOURCE,
                    created,
                    Map.of("code", source.code()));
            return created;
        });
        return findSource(sourceId);
    }

    @Override
    public ManagedSource updateSource(UUID adminId, UUID sourceId, SourceChange change) {
        audited(adminId, sourceAttempts(sourceId, change), () -> {
            ManagedSource current = sources.findForUpdate(sourceId).orElseThrow(SourceAdministrationService::notFound);
            requireVersion(current.version(), change.version());
            SourceSettings next = new SourceSettings(
                    valueOr(change.name(), current.name()),
                    valueOr(change.homepageUrl(), current.homepageUrl()),
                    valueOr(change.requestIntervalSeconds(), current.requestIntervalSeconds()),
                    optionalOr(change.dailyRequestLimit(), current.dailyRequestLimit()),
                    optionalOr(change.license(), current.license()),
                    optionalOr(change.attributionText(), current.attributionText()),
                    optionalOr(change.feedTimeZone(), current.feedTimeZone()),
                    valueOr(change.enabled(), current.enabled()));
            List<String> changedFields = changedFields(current, next);
            boolean enabledChanged = next.enabled() != current.enabled();
            if (changedFields.isEmpty() && !enabledChanged) {
                return null;
            }

            sources.update(sourceId, next);
            if (!changedFields.isEmpty()) {
                recordSuccess(
                        adminId,
                        AuditAction.SOURCE_UPDATED,
                        AuditTargetType.SOURCE,
                        sourceId,
                        Map.of("fields", changedFields));
            }
            if (enabledChanged) {
                AuditAction action = next.enabled() ? AuditAction.SOURCE_ENABLED : AuditAction.SOURCE_DISABLED;
                recordSuccess(adminId, action, AuditTargetType.SOURCE, sourceId, Map.of());
            }
            return null;
        });
        return findSource(sourceId);
    }

    @Override
    public int requestFetch(UUID adminId, UUID sourceId) {
        Attempt attempt = new Attempt(AuditAction.FETCH_REQUESTED, AuditTargetType.SOURCE, sourceId, Map.of());
        return audited(adminId, List.of(attempt), () -> {
            ManagedSource source = sources.findForUpdate(sourceId).orElseThrow(SourceAdministrationService::notFound);
            // Devre dışı kaynağın beslemelerini işçi zaten okumaz; istek karşılanamaz (sözleşme 6.2).
            if (!source.enabled()) {
                throw conflict(ErrorCode.INVALID_STATE_TRANSITION);
            }
            int feedCount = feeds.requestFetch(sourceId);
            recordSuccess(
                    adminId,
                    AuditAction.FETCH_REQUESTED,
                    AuditTargetType.SOURCE,
                    sourceId,
                    Map.of("feedCount", feedCount));
            return feedCount;
        });
    }

    @Override
    public ManagedFeed createFeed(UUID adminId, UUID sourceId, NewFeed feed) {
        requireCategory(feed.defaultCategoryCode());
        Attempt attempt = new Attempt(
                AuditAction.FEED_CREATED, null, null, Map.of("sourceId", sourceId.toString(), "name", feed.name()));
        UUID feedId = audited(adminId, List.of(attempt), () -> {
            sources.findForUpdate(sourceId).orElseThrow(SourceAdministrationService::notFound);
            UUID created = feeds.insert(sourceId, feed);
            recordSuccess(
                    adminId,
                    AuditAction.FEED_CREATED,
                    AuditTargetType.FEED,
                    created,
                    Map.of("sourceId", sourceId.toString(), "name", feed.name()));
            return created;
        });
        return feeds.findById(feedId).orElseThrow(SourceAdministrationService::notFound);
    }

    @Override
    public ManagedFeed updateFeed(UUID adminId, UUID feedId, FeedChange change) {
        // Alan gönderilmediyse Optional'ın kendisi null'dır (değişmez); yalnızca bir değer verildiyse denetlenir.
        if (change.defaultCategoryCode() != null) {
            change.defaultCategoryCode().ifPresent(this::requireCategory);
        }
        audited(adminId, feedAttempts(feedId, change), () -> {
            ManagedFeed current = feeds.findForUpdate(feedId).orElseThrow(SourceAdministrationService::notFound);
            requireVersion(current.version(), change.version());
            boolean enabled = valueOr(change.enabled(), current.enabled());
            boolean reenabled = enabled && !current.enabled();
            boolean disabling = !enabled && current.enabled();
            // Devre dışı kalan beslemenin nedeni: yöneticinin kapattığı MANUAL; zaten kapalıysa nedeni değişmez.
            String disabledReason = enabled ? null : disabling ? MANUAL : current.disabledReason();
            String url = valueOr(change.url(), current.url());
            FeedSettings next = new FeedSettings(
                    valueOr(change.name(), current.name()),
                    url,
                    optionalOr(change.defaultCategoryCode(), current.defaultCategoryCode()),
                    valueOr(change.useItemCategories(), current.useItemCategories()),
                    valueOr(change.fetchIntervalMinutes(), current.fetchIntervalMinutes()),
                    enabled,
                    disabledReason,
                    !url.equals(current.url()),
                    reenabled,
                    reenabled && AUTO.equals(current.disabledReason()));
            List<String> changedFields = changedFields(current, next);
            if (changedFields.isEmpty() && !reenabled && !disabling) {
                return null;
            }

            feeds.update(feedId, next);
            if (!changedFields.isEmpty()) {
                recordSuccess(
                        adminId,
                        AuditAction.FEED_UPDATED,
                        AuditTargetType.FEED,
                        feedId,
                        Map.of("fields", changedFields));
            }
            if (reenabled) {
                recordSuccess(
                        adminId,
                        AuditAction.FEED_ENABLED,
                        AuditTargetType.FEED,
                        feedId,
                        Map.of("previousReason", current.disabledReason()));
            }
            if (disabling) {
                recordSuccess(adminId, AuditAction.FEED_DISABLED, AuditTargetType.FEED, feedId, Map.of());
            }
            return null;
        });
        return feeds.findById(feedId).orElseThrow(SourceAdministrationService::notFound);
    }

    /**
     * İşi bir veritabanı işleminde çalıştırır. Kural ihlalinde (409) işlem geri alınmıştır; her denenen işlem
     * için {@code FAILURE} kaydı işlemin dışında yazılır ve hata yine istemciye döner. Benzersizlik ihlali
     * (aynı kod, ad veya adres) de {@code 409 ALREADY_EXISTS} olur. Kaydın bulunamaması (404) ve geçersiz girdi
     * (400) deneme sayılmaz, yazılmaz.
     */
    private <T> T audited(UUID adminId, List<Attempt> attempts, Supplier<T> work) {
        try {
            return transactionTemplate.execute(transaction -> work.get());
        } catch (DuplicateKeyException exception) {
            recordFailures(adminId, attempts, ErrorCode.ALREADY_EXISTS);
            throw new ApiException(HttpStatus.CONFLICT, ErrorCode.ALREADY_EXISTS, exception);
        } catch (ApiException exception) {
            if (exception.status() == HttpStatus.CONFLICT) {
                recordFailures(adminId, attempts, exception.code());
            }
            throw exception;
        }
    }

    private void recordFailures(UUID adminId, List<Attempt> attempts, ErrorCode code) {
        try {
            for (Attempt attempt : attempts) {
                Map<String, Object> details = new HashMap<>(attempt.details());
                details.put("code", code.name());
                auditLog.record(AuditEvent.failure(
                        adminId, attempt.action(), attempt.targetType(), attempt.targetId(), details));
            }
        } catch (DataAccessException exception) {
            log.error("Reddedilen kaynak yönetimi işleminin audit kaydı yazılamadı", exception);
        }
    }

    /** Kaynak değişikliğinde istenen işlemler: ayar değişikliği ve/veya etkinleştirme/devre dışı bırakma. */
    private static List<Attempt> sourceAttempts(UUID sourceId, SourceChange change) {
        List<String> requested = new ArrayList<>();
        addIfRequested(requested, "name", change.name());
        addIfRequested(requested, "homepageUrl", change.homepageUrl());
        addIfRequested(requested, "requestIntervalSeconds", change.requestIntervalSeconds());
        addIfRequested(requested, "dailyRequestLimit", change.dailyRequestLimit());
        addIfRequested(requested, "license", change.license());
        addIfRequested(requested, "attributionText", change.attributionText());
        addIfRequested(requested, "feedTimeZone", change.feedTimeZone());
        List<Attempt> attempts = new ArrayList<>();
        if (!requested.isEmpty()) {
            attempts.add(new Attempt(
                    AuditAction.SOURCE_UPDATED, AuditTargetType.SOURCE, sourceId, Map.of("fields", requested)));
        }
        if (change.enabled() != null) {
            AuditAction action = change.enabled() ? AuditAction.SOURCE_ENABLED : AuditAction.SOURCE_DISABLED;
            attempts.add(new Attempt(action, AuditTargetType.SOURCE, sourceId, Map.of()));
        }
        return attempts;
    }

    private static List<Attempt> feedAttempts(UUID feedId, FeedChange change) {
        List<String> requested = new ArrayList<>();
        addIfRequested(requested, "name", change.name());
        addIfRequested(requested, "url", change.url());
        addIfRequested(requested, "defaultCategoryCode", change.defaultCategoryCode());
        addIfRequested(requested, "useItemCategories", change.useItemCategories());
        addIfRequested(requested, "fetchIntervalMinutes", change.fetchIntervalMinutes());
        List<Attempt> attempts = new ArrayList<>();
        if (!requested.isEmpty()) {
            attempts.add(
                    new Attempt(AuditAction.FEED_UPDATED, AuditTargetType.FEED, feedId, Map.of("fields", requested)));
        }
        if (change.enabled() != null) {
            AuditAction action = change.enabled() ? AuditAction.FEED_ENABLED : AuditAction.FEED_DISABLED;
            attempts.add(new Attempt(action, AuditTargetType.FEED, feedId, Map.of()));
        }
        return attempts;
    }

    private static void addIfRequested(List<String> fields, String name, Object value) {
        if (value != null) {
            fields.add(name);
        }
    }

    /** Ayarlardan gerçekten değişenlerin adları (audit kaydında yalnızca adlar tutulur, değerler değil). */
    private static List<String> changedFields(ManagedSource current, SourceSettings next) {
        List<String> fields = new ArrayList<>();
        addIfChanged(fields, "name", current.name(), next.name());
        addIfChanged(fields, "homepageUrl", current.homepageUrl(), next.homepageUrl());
        addIfChanged(fields, "requestIntervalSeconds", current.requestIntervalSeconds(), next.requestIntervalSeconds());
        addIfChanged(fields, "dailyRequestLimit", current.dailyRequestLimit(), next.dailyRequestLimit());
        addIfChanged(fields, "license", current.license(), next.license());
        addIfChanged(fields, "attributionText", current.attributionText(), next.attributionText());
        addIfChanged(fields, "feedTimeZone", current.feedTimeZone(), next.feedTimeZone());
        return fields;
    }

    private static List<String> changedFields(ManagedFeed current, FeedSettings next) {
        List<String> fields = new ArrayList<>();
        addIfChanged(fields, "name", current.name(), next.name());
        addIfChanged(fields, "url", current.url(), next.url());
        addIfChanged(fields, "defaultCategoryCode", current.defaultCategoryCode(), next.defaultCategoryCode());
        addIfChanged(fields, "useItemCategories", current.useItemCategories(), next.useItemCategories());
        addIfChanged(fields, "fetchIntervalMinutes", current.fetchIntervalMinutes(), next.fetchIntervalMinutes());
        return fields;
    }

    private static void addIfChanged(List<String> fields, String name, Object before, Object after) {
        if (!Objects.equals(before, after)) {
            fields.add(name);
        }
    }

    /** Değişiklikte verilmeyen ({@code null}) alan eski değerini korur. */
    private static <T> T valueOr(T requested, T current) {
        return requested == null ? current : requested;
    }

    /** Boş bırakılabilen alan: {@code null} değişmez, boş {@code Optional} boşaltır. */
    private static <T> T optionalOr(Optional<T> requested, T current) {
        return requested == null ? current : requested.orElse(null);
    }

    private void requireCategory(String code) {
        if (code != null && !feeds.categoryExists(code)) {
            throw new InvalidRequestException(
                    List.of(new FieldError("defaultCategoryCode", FieldError.Code.INVALID_VALUE)));
        }
    }

    private static void requireVersion(int current, int requested) {
        if (current != requested) {
            throw conflict(ErrorCode.VERSION_CONFLICT);
        }
    }

    private ManagedSource withFeeds(ManagedSource source) {
        return new ManagedSource(
                source.id(),
                source.code(),
                source.name(),
                source.homepageUrl(),
                source.readerType(),
                source.language(),
                source.requestIntervalSeconds(),
                source.dailyRequestLimit(),
                source.license(),
                source.attributionText(),
                source.feedTimeZone(),
                source.enabled(),
                source.purgeRequestedAt(),
                source.version(),
                feeds.findBySource(source.id()));
    }

    private void recordSuccess(
            UUID adminId, AuditAction action, AuditTargetType targetType, UUID targetId, Map<String, Object> details) {
        auditLog.record(AuditEvent.success(adminId, action, targetType, targetId, details));
    }

    private static ApiException notFound() {
        return new ApiException(HttpStatus.NOT_FOUND, ErrorCode.NOT_FOUND);
    }

    private static ApiException conflict(ErrorCode code) {
        return new ApiException(HttpStatus.CONFLICT, code);
    }
}
