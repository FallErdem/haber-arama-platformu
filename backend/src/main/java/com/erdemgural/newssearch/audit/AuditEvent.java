package com.erdemgural.newssearch.audit;

import java.util.Map;
import java.util.Objects;
import java.util.UUID;

/**
 * Yazılacak bir audit kaydı: kim, ne yaptı, neye yaptı, sonuç ne oldu (FG-AL-02). Zaman, istek kimliği
 * ve IP adresi kaydı yazan modülce eklenir; çağıranın vermesi gerekmez.
 *
 * @param actorUserId işlemi yapan kullanıcı; API'nin yazdığı her kayıtta bir kullanıcı vardır
 * @param success işlem yapıldıysa {@code true}; reddedilen istek veya iş kuralı nedeniyle yapılamayan
 *     işlemde {@code false}
 * @param targetType işlemin yapıldığı nesnenin türü; nesnesi olmayan işlemde (reddedilen istek) {@code null}
 * @param targetId işlemin yapıldığı nesnenin kimliği; nesnesi yoksa {@code null}
 * @param details işleme özgü, önceden belirlenmiş alanlar. İstek gövdesi, başlıklar, token, parola veya
 *     arama ifadesi hiçbir zaman yazılmaz (ADR-0016 4. bölüm; FG-AL-04, FG-AL-05)
 */
public record AuditEvent(
        UUID actorUserId,
        AuditAction action,
        AuditTargetType targetType,
        UUID targetId,
        boolean success,
        Map<String, Object> details) {

    public AuditEvent {
        Objects.requireNonNull(actorUserId, "actorUserId");
        Objects.requireNonNull(action, "action");
        details = details == null ? Map.of() : Map.copyOf(details);
    }

    /** Bir nesne üzerinde başarıyla yapılmış işlem. */
    public static AuditEvent success(
            UUID actorUserId,
            AuditAction action,
            AuditTargetType targetType,
            UUID targetId,
            Map<String, Object> details) {
        return new AuditEvent(actorUserId, action, targetType, targetId, true, details);
    }

    /** Nesnesi olmayan, başarısız bir işlem (örneğin reddedilen istek). */
    public static AuditEvent failure(UUID actorUserId, AuditAction action, Map<String, Object> details) {
        return new AuditEvent(actorUserId, action, null, null, false, details);
    }

    /** Bir nesne üzerinde denenip iş kuralı nedeniyle yapılamamış işlem (örneğin son yöneticinin rolünü düşürmek). */
    public static AuditEvent failure(
            UUID actorUserId,
            AuditAction action,
            AuditTargetType targetType,
            UUID targetId,
            Map<String, Object> details) {
        return new AuditEvent(actorUserId, action, targetType, targetId, false, details);
    }
}
