package com.erdemgural.newssearch.identity;

import com.erdemgural.newssearch.web.PageParameters;
import com.erdemgural.newssearch.web.PageResponse;
import java.util.UUID;

/**
 * Kullanıcı yönetimi (FG-YP-01 – 03; API sözleşmesi 6.1). Kullanıcı tablosu ve durum kuralları bu
 * modüldedir; yönetim panelinin uç noktaları ({@code admin} modülü) bu arayüzü kullanır.
 *
 * <p>Değiştiren metotlar, kural ihlalinde {@code 409} durumlu bir {@code ApiException} fırlatır:
 * {@code INVALID_STATE_TRANSITION}, {@code VERSION_CONFLICT} veya {@code LAST_ACTIVE_ADMIN}. Kullanıcı
 * yoksa {@code 404 NOT_FOUND}. Başarılı değişiklik de reddedilen deneme de audit log'a yazılır.
 *
 * @see ManagedUser
 */
public interface UserAdministration {

    /** Kullanıcılar, kayıt zamanına göre yeniden eskiye. */
    PageResponse<ManagedUser> list(UserFilter filter, PageParameters page);

    /** Onay bekleyen kullanıcıyı aktif yapar; rolü {@code USER} olur. */
    ManagedUser approve(UUID adminId, UUID userId);

    /** Onay bekleyen kullanıcıyı reddeder. */
    ManagedUser reject(UUID adminId, UUID userId);

    /** Aktif veya pasif kullanıcının rolünü ve/veya durumunu değiştirir. */
    ManagedUser change(UUID adminId, UUID userId, UserChange change);
}
