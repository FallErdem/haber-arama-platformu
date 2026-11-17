package com.erdemgural.newssearch.ingestion.internal;

import java.nio.charset.StandardCharsets;
import java.security.InvalidKeyException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Base64;
import java.util.Optional;
import java.util.UUID;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.stereotype.Component;

/**
 * Görsel adreslerini imzalar ve doğrular (API sözleşmesi 4.4).
 *
 * <p>{@code <img>} etiketi istek başlığı ekleyemediği için görsel uç noktası token yerine imzalı
 * adres ister. İmza, görselin kimliği ile son geçerlilik zamanının, yalnızca API'nin bildiği bir
 * anahtarla hesaplanan HMAC-SHA256 değeridir: anahtarı bilmeyen biri başka bir görselin ya da daha
 * uzun süreli bir adresin imzasını üretemez.
 */
@Component
class MediaUrlSigner {

    static final String PATH_PREFIX = "/api/v1/media/";

    /** Adres, üretildiği saatin başlangıcından bu kadar sonra geçersiz olur: 1 ile 2 saat arası. */
    static final Duration VALIDITY = Duration.ofHours(2);

    private static final String ALGORITHM = "HmacSHA256";

    private final SecretKeySpec key;
    private final Clock clock;

    MediaUrlSigner(MediaProperties properties, Clock clock) {
        this.key = new SecretKeySpec(properties.signingKey().getBytes(StandardCharsets.UTF_8), ALGORITHM);
        this.clock = clock;
    }

    /**
     * Görselin imzalı adresi: {@code /api/v1/media/{id}?exp={saniye}&sig={imza}}. Süre saatin
     * başından sayıldığı için aynı saat içinde üretilen adresler aynıdır; tarayıcı görseli önbellekten
     * kullanabilir.
     */
    String signedUrl(UUID mediaId) {
        long expiresAt =
                clock.instant().truncatedTo(ChronoUnit.HOURS).plus(VALIDITY).getEpochSecond();
        return PATH_PREFIX + mediaId + "?exp=" + expiresAt + "&sig=" + signature(mediaId, expiresAt);
    }

    /**
     * Adres geçerliyse son geçerlilik zamanını döner; imza tutmuyorsa, süre dolmuşsa veya
     * parametreler eksik ya da bozuksa boş döner.
     */
    Optional<Instant> verify(UUID mediaId, String exp, String sig) {
        if (exp == null || sig == null) {
            return Optional.empty();
        }
        long expiresAt;
        try {
            expiresAt = Long.parseLong(exp);
        } catch (NumberFormatException exception) {
            return Optional.empty();
        }
        byte[] expected = signature(mediaId, expiresAt).getBytes(StandardCharsets.US_ASCII);
        // MessageDigest.isEqual karşılaştırmayı her zaman aynı sürede yapar; ilk farklı karakterde
        // durmaz. Böylece yanıt süresinden imzanın kaç karakterinin doğru olduğu çıkarılamaz.
        if (!MessageDigest.isEqual(expected, sig.getBytes(StandardCharsets.US_ASCII))) {
            return Optional.empty();
        }
        Instant expiry = Instant.ofEpochSecond(expiresAt);
        return clock.instant().isBefore(expiry) ? Optional.of(expiry) : Optional.empty();
    }

    /** İmzalanan metin "{kimlik}.{saniye}"; sonuç adreste kullanılabilen Base64 (dolgusuz). */
    private String signature(UUID mediaId, long expiresAt) {
        try {
            Mac mac = Mac.getInstance(ALGORITHM);
            mac.init(key);
            byte[] digest = mac.doFinal((mediaId + "." + expiresAt).getBytes(StandardCharsets.UTF_8));
            return Base64.getUrlEncoder().withoutPadding().encodeToString(digest);
        } catch (NoSuchAlgorithmException | InvalidKeyException exception) {
            // HmacSHA256 her Java kurulumunda bulunur; buraya düşmek bir yapılandırma hatasıdır.
            throw new IllegalStateException("Görsel adresi imzalanamadı", exception);
        }
    }
}
