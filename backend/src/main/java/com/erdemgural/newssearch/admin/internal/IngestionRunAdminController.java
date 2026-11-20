package com.erdemgural.newssearch.admin.internal;

import com.erdemgural.newssearch.ingestion.IngestionHistory;
import com.erdemgural.newssearch.ingestion.IngestionRun;
import com.erdemgural.newssearch.ingestion.IngestionRunFilter;
import com.erdemgural.newssearch.web.FieldError;
import com.erdemgural.newssearch.web.FieldError.Code;
import com.erdemgural.newssearch.web.InvalidRequestException;
import com.erdemgural.newssearch.web.PageParameters;
import com.erdemgural.newssearch.web.PageResponse;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** Toplama geçmişi (API sözleşmesi 6.5; FG-YP-05). Yalnızca {@code ADMIN} rolüne açıktır. */
@RestController
@RequestMapping("/api/v1/admin/ingestion-runs")
class IngestionRunAdminController {

    private static final List<String> STATUSES = List.of("RUNNING", "SUCCEEDED", "NOT_MODIFIED", "FAILED");

    private final IngestionHistory ingestionHistory;

    IngestionRunAdminController(IngestionHistory ingestionHistory) {
        this.ingestionHistory = ingestionHistory;
    }

    /** Parametreler metin olarak alınır; geçersiz olanların hepsi alan adı ve koduyla birlikte bildirilir. */
    @GetMapping
    PageResponse<IngestionRun> list(
            @RequestParam(required = false) String sourceId,
            @RequestParam(required = false) String feedId,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String from,
            @RequestParam(required = false) String to,
            @RequestParam(required = false) String page,
            @RequestParam(required = false) String size) {
        List<FieldError> errors = new ArrayList<>();
        UUID source = parseUuid("sourceId", sourceId, errors);
        UUID feed = parseUuid("feedId", feedId, errors);
        String statusFilter = blankToNull(status);
        if (statusFilter != null && !STATUSES.contains(statusFilter)) {
            errors.add(new FieldError("status", Code.INVALID_VALUE));
        }
        Instant fromInstant = parseInstant("from", from, errors);
        Instant toInstant = parseInstant("to", to, errors);
        if (fromInstant != null && toInstant != null && fromInstant.isAfter(toInstant)) {
            errors.add(new FieldError("from", Code.INVALID_RANGE));
        }
        PageParameters pageParameters = PageParameters.parse(page, size, errors);
        if (!errors.isEmpty()) {
            throw new InvalidRequestException(errors);
        }
        return ingestionHistory.list(
                new IngestionRunFilter(source, feed, statusFilter, fromInstant, toInstant), pageParameters);
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
