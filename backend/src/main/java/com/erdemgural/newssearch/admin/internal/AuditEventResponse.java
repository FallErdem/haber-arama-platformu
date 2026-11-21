package com.erdemgural.newssearch.admin.internal;

import com.erdemgural.newssearch.audit.AuditRecord;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;

/**
 * Yönetim panelindeki bir audit kaydı (API sözleşmesi 6.8).
 *
 * @param actorEmail işlemi yapan kullanıcının e-postası; sistem kaydında {@code null}
 */
record AuditEventResponse(
        UUID id,
        Instant occurredAt,
        String actorType,
        UUID actorUserId,
        String actorEmail,
        String action,
        String targetType,
        UUID targetId,
        String result,
        String requestId,
        String ipAddress,
        Map<String, Object> details) {

    /** @param emails kullanıcı kimliğinden e-postaya; sistem kaydının kullanıcısı yoktur */
    static AuditEventResponse from(AuditRecord record, Map<UUID, String> emails) {
        return new AuditEventResponse(
                record.id(),
                record.occurredAt(),
                record.actorType(),
                record.actorUserId(),
                record.actorUserId() == null ? null : emails.get(record.actorUserId()),
                record.action(),
                record.targetType(),
                record.targetId(),
                record.result(),
                record.requestId(),
                record.ipAddress(),
                record.details());
    }
}
