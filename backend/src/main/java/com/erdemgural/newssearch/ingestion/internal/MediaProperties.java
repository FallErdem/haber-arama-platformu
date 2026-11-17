package com.erdemgural.newssearch.ingestion.internal;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Görsellerin sunulmasıyla ilgili ayarlar ({@code newssearch.media.*}).
 *
 * @param signingKey görsel adreslerini imzalayan gizli anahtar; bütün API kopyalarında aynıdır
 * @param storageUrl nesne depolamanın (MinIO) adresi
 * @param accessKey nesne depolamadaki kullanıcı; API'nin kullanıcısı yalnızca okuyabilir
 * @param secretKey bu kullanıcının şifresi
 * @param bucket görsellerin bulunduğu kova
 */
@ConfigurationProperties("newssearch.media")
record MediaProperties(String signingKey, String storageUrl, String accessKey, String secretKey, String bucket) {

    /** HMAC-SHA256 için önerilen en kısa anahtar: özet uzunluğu kadar, 32 bayt. */
    static final int MIN_SIGNING_KEY_LENGTH = 32;

    MediaProperties {
        // Anahtar eksik veya kısaysa uygulama hiç açılmaz; imzasız ya da kolay tahmin edilen adres üretilmez.
        if (signingKey == null || signingKey.length() < MIN_SIGNING_KEY_LENGTH) {
            throw new IllegalArgumentException(
                    "MEDIA_SIGNING_KEY en az " + MIN_SIGNING_KEY_LENGTH + " karakter olmalıdır");
        }
    }

    @Override
    public String toString() {
        // Ayarlar loga yazılırsa anahtar ve şifre görünmez.
        return "MediaProperties[storageUrl=" + storageUrl + ", accessKey=" + accessKey + ", bucket=" + bucket + "]";
    }
}
