package com.erdemgural.newssearch.web;

/**
 * Hata yanıtlarındaki makine tarafından okunan {@code code} değerleri (API
 * sözleşmesi 2.6). Arayüz, kullanıcıya göstereceği metni bu koddan üretir.
 * Sözleşmedeki diğer kodlar, onları kullanan işlevlerle birlikte eklenir.
 */
public enum ErrorCode {
    VALIDATION_FAILED,
    PAGE_LIMIT_EXCEEDED,
    /** Dışa aktarılacak kayıt sayısı sınırı aşıyor (audit CSV'sinde 100.000). */
    EXPORT_TOO_LARGE,
    UNAUTHENTICATED,
    USER_PENDING_APPROVAL,
    USER_REJECTED,
    USER_PASSIVE,
    FORBIDDEN,
    MEDIA_URL_INVALID,
    NOT_FOUND,
    /** İyimser kilitleme çakışması: kayıt, istemcinin gördüğü sürümden sonra değişmiş (sözleşme 2.5). */
    VERSION_CONFLICT,
    /** İşlem kaydın mevcut durumunda yapılamıyor (örneğin onay bekleyen olmayan kullanıcıyı onaylamak). */
    INVALID_STATE_TRANSITION,
    /** İşlem sistemdeki son aktif yöneticiyi kaldıracak (FG-YP-03). */
    LAST_ACTIVE_ADMIN,
    /** Benzersiz olması gereken bir değer (kaynak kodu veya adı, besleme adresi veya adı) zaten var. */
    ALREADY_EXISTS,
    SEARCH_UNAVAILABLE,
    MEDIA_UNAVAILABLE,
    INTERNAL_ERROR
}
