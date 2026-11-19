package com.erdemgural.newssearch.admin.internal;

import com.erdemgural.newssearch.identity.ManagedUser;
import java.time.Instant;
import java.util.UUID;

/**
 * Yönetim panelindeki bir kullanıcı (API sözleşmesi 6.1).
 *
 * @param version rol veya durum değiştirme isteğinde geri gönderilir (sözleşme 2.5)
 */
record AdminUserResponse(
        UUID id, String email, String displayName, String role, String status, Instant createdAt, int version) {

    static AdminUserResponse from(ManagedUser user) {
        return new AdminUserResponse(
                user.id(),
                user.email(),
                user.displayName(),
                user.role().name(),
                user.status().name(),
                user.createdAt(),
                user.version());
    }
}
