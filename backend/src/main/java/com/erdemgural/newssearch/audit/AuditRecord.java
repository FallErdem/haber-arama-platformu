package com.erdemgural.newssearch.audit;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

/**
 * Okunan bir audit kaydı ({@code audit_events}; veri modeli 3.13). Yazılacak kayıt {@link AuditEvent}'tir;
 * bu kayıt ise veritabanında olduğu gibidir: işçinin yazdığı sistem kayıtları da bu biçimde okunur.
 *
 * @param actorType {@code USER} veya {@code SYSTEM}
 * @param actorUserId işlemi yapan kullanıcı; sistem kaydında {@code null}
 * @param result {@code SUCCESS} veya {@code FAILURE}
 * @param ipAddress isteğin geldiği adres; işçinin kayıtlarında {@code null}
 * @param details işleme özgü alanlar; ayrıntısı olmayan kayıtta boş
 */
public record AuditRecord(
        UUID id,
        Instant occurredAt,
        String actorType,
        UUID actorUserId,
        String action,
        String targetType,
        UUID targetId,
        String result,
        String requestId,
        String ipAddress,
        Map<String, Object> details) {}
