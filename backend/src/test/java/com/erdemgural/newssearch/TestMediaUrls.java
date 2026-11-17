package com.erdemgural.newssearch;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.UUID;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/**
 * Testlerde görsel adreslerini, uygulamanın imzalayıcısından bağımsız olarak üretir. API sözleşmesinin
 * 4.4 bölümündeki tanımın ikinci bir uygulamasıdır: uygulamanın ürettiği adresler bununla aynı çıkarsa
 * biçim sözleşmeye uyuyordur; ayrıca süresi dolmuş veya bozuk adresler üretmeye yarar.
 */
public final class TestMediaUrls {

    /** Testlerdeki imza anahtarı; yalnızca test konteynerlerine aittir. */
    public static final String SIGNING_KEY = "test-imza-anahtari-en-az-otuz-iki-karakter";

    private TestMediaUrls() {}

    /** {@code /api/v1/media/{id}?exp=...&sig=...}; imza HMAC-SHA256("{id}.{exp}"), dolgusuz Base64 (URL). */
    public static String signedPath(UUID mediaId, Instant expiresAt) {
        long exp = expiresAt.getEpochSecond();
        return "/api/v1/media/" + mediaId + "?exp=" + exp + "&sig=" + signature(mediaId, exp);
    }

    public static String signature(UUID mediaId, long exp) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(SIGNING_KEY.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            byte[] digest = mac.doFinal((mediaId + "." + exp).getBytes(StandardCharsets.UTF_8));
            return Base64.getUrlEncoder().withoutPadding().encodeToString(digest);
        } catch (Exception exception) {
            throw new IllegalStateException(exception);
        }
    }
}
