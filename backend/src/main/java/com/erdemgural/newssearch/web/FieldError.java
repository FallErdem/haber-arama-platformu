package com.erdemgural.newssearch.web;

/**
 * Bir girdi alanındaki doğrulama hatası (API sözleşmesi 2.6, {@code errors} alanı). Arayüz,
 * kullanıcıya göstereceği metni alan adı ve koddan kendi dil dosyalarıyla üretir.
 */
public record FieldError(String field, Code code) {

    public enum Code {
        /** Değer beklenen biçimde değil veya izin verilen değerlerden biri değil. */
        INVALID_VALUE,
        /** Sayı izin verilen en küçük değerden küçük. */
        MIN_VALUE,
        /** Sayı izin verilen en büyük değerden büyük. */
        MAX_VALUE,
        /** Metin izin verilen uzunluktan uzun. */
        MAX_LENGTH,
        /** Aralığın başlangıcı bitişinden sonra. */
        INVALID_RANGE
    }
}
