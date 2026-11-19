package com.erdemgural.newssearch.identity;

import java.time.Instant;
import java.util.UUID;

/**
 * Yönetim panelinde gösterilen kullanıcı (FG-YP-01).
 *
 * @param version iyimser kilitleme sürümü; kullanıcı her değiştiğinde artar. Rol veya durum değiştirme
 *     isteği bu değeri geri gönderir; kayıt bu arada değişmişse istek reddedilir (API sözleşmesi 2.5)
 */
public record ManagedUser(
        UUID id, String email, String displayName, UserRole role, UserStatus status, Instant createdAt, int version) {

    /** Son aktif yönetici kuralının (FG-YP-03) saydığı kullanıcı. */
    public boolean isActiveAdmin() {
        return role == UserRole.ADMIN && status == UserStatus.ACTIVE;
    }
}
