package com.erdemgural.newssearch.web;

/**
 * Hata yanıtlarındaki makine tarafından okunan {@code code} değerleri (API
 * sözleşmesi 2.6). Arayüz, kullanıcıya göstereceği metni bu koddan üretir.
 * Sözleşmedeki diğer kodlar, onları kullanan işlevlerle birlikte eklenir.
 */
public enum ErrorCode {
    VALIDATION_FAILED,
    PAGE_LIMIT_EXCEEDED,
    UNAUTHENTICATED,
    USER_PENDING_APPROVAL,
    USER_REJECTED,
    USER_PASSIVE,
    FORBIDDEN,
    MEDIA_URL_INVALID,
    NOT_FOUND,
    SEARCH_UNAVAILABLE,
    MEDIA_UNAVAILABLE,
    INTERNAL_ERROR
}
