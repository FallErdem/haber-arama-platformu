package com.erdemgural.newssearch.ingestion.internal;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.erdemgural.newssearch.TestMediaUrls;
import java.net.URI;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;
import java.util.stream.Stream;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/** Görsel adreslerinin imzalanması ve doğrulanması (API sözleşmesi 4.4); Spring'siz, sabit saatle. */
class MediaUrlSignerTests {

    private static final UUID MEDIA_ID = UUID.fromString("019a0000-0000-7000-8000-0000000000aa");
    private static final UUID OTHER_ID = UUID.fromString("019a0000-0000-7000-8000-0000000000bb");

    /** 17 Kasım 2026, 10:25 UTC. */
    private static final Instant NOW = Instant.parse("2026-11-17T10:25:00Z");

    private static MediaUrlSigner signerAt(Instant now) {
        MediaProperties properties =
                new MediaProperties(TestMediaUrls.SIGNING_KEY, "http://minio:9000", "news-api", "x", "media");
        return new MediaUrlSigner(properties, Clock.fixed(now, ZoneOffset.UTC));
    }

    private static Map<String, String> query(String url) {
        return Stream.of(URI.create(url).getQuery().split("&"))
                .map(pair -> pair.split("=", 2))
                .collect(Collectors.toMap(pair -> pair[0], pair -> pair[1]));
    }

    @Test
    @DisplayName("adres, saatin başından iki saat sonrasına kadar geçerlidir")
    void urlIsValidUntilTwoHoursAfterTheStartOfTheHour() {
        String url = signerAt(NOW).signedUrl(MEDIA_ID);

        assertThat(url).startsWith("/api/v1/media/" + MEDIA_ID + "?exp=");
        // 10:25'te üretilen adres 12:00'ye kadar geçerli: en az 1, en fazla 2 saat.
        assertThat(query(url))
                .containsEntry(
                        "exp",
                        String.valueOf(Instant.parse("2026-11-17T12:00:00Z").getEpochSecond()));
    }

    @Test
    @DisplayName("imza sözleşmedeki tanıma uyar: HMAC-SHA256(\"{id}.{exp}\"), dolgusuz Base64")
    void signatureFollowsTheContract() {
        String url = signerAt(NOW).signedUrl(MEDIA_ID);

        assertThat(url).isEqualTo(TestMediaUrls.signedPath(MEDIA_ID, Instant.parse("2026-11-17T12:00:00Z")));
    }

    @Test
    @DisplayName("aynı saat içinde üretilen adresler aynıdır; tarayıcı görseli önbellekten kullanabilir")
    void urlsWithinTheSameHourAreIdentical() {
        assertThat(signerAt(Instant.parse("2026-11-17T10:01:00Z")).signedUrl(MEDIA_ID))
                .isEqualTo(signerAt(Instant.parse("2026-11-17T10:59:59Z")).signedUrl(MEDIA_ID));
        assertThat(signerAt(Instant.parse("2026-11-17T11:00:00Z")).signedUrl(MEDIA_ID))
                .isNotEqualTo(signerAt(Instant.parse("2026-11-17T10:59:59Z")).signedUrl(MEDIA_ID));
    }

    @Test
    @DisplayName("geçerli adres doğrulanır ve son geçerlilik zamanı döner")
    void validUrlIsAccepted() {
        Map<String, String> params = query(signerAt(NOW).signedUrl(MEDIA_ID));

        assertThat(signerAt(NOW.plusSeconds(3000)).verify(MEDIA_ID, params.get("exp"), params.get("sig")))
                .contains(Instant.parse("2026-11-17T12:00:00Z"));
    }

    @Test
    @DisplayName("süresi dolmuş adres reddedilir")
    void expiredUrlIsRejected() {
        Map<String, String> params = query(signerAt(NOW).signedUrl(MEDIA_ID));

        assertThat(signerAt(Instant.parse("2026-11-17T12:00:00Z"))
                        .verify(MEDIA_ID, params.get("exp"), params.get("sig")))
                .isEmpty();
    }

    @Test
    @DisplayName("başka bir görselin imzası, değiştirilmiş süre veya bozuk imza reddedilir")
    void tamperedUrlIsRejected() {
        MediaUrlSigner signer = signerAt(NOW);
        Map<String, String> params = query(signer.signedUrl(MEDIA_ID));
        String longerExpiry = String.valueOf(Long.parseLong(params.get("exp")) + 86_400);

        assertThat(signer.verify(OTHER_ID, params.get("exp"), params.get("sig")))
                .isEmpty();
        assertThat(signer.verify(MEDIA_ID, longerExpiry, params.get("sig"))).isEmpty();
        assertThat(signer.verify(MEDIA_ID, params.get("exp"), params.get("sig") + "x"))
                .isEmpty();
    }

    @Test
    @DisplayName("eksik veya sayı olmayan parametreler reddedilir")
    void missingOrMalformedParametersAreRejected() {
        MediaUrlSigner signer = signerAt(NOW);

        assertThat(signer.verify(MEDIA_ID, null, "imza")).isEmpty();
        assertThat(signer.verify(MEDIA_ID, "1795000000", null)).isEmpty();
        assertThat(signer.verify(MEDIA_ID, "yarın", "imza")).isEmpty();
    }

    @Test
    @DisplayName("başka bir anahtarla üretilmiş imza reddedilir")
    void signatureFromAnotherKeyIsRejected() {
        MediaProperties otherKey =
                new MediaProperties("baska-bir-anahtar-en-az-otuz-iki-karakter-uzunlukta", "u", "a", "s", "b");
        Map<String, String> params =
                query(new MediaUrlSigner(otherKey, Clock.fixed(NOW, ZoneOffset.UTC)).signedUrl(MEDIA_ID));

        assertThat(signerAt(NOW).verify(MEDIA_ID, params.get("exp"), params.get("sig")))
                .isEmpty();
    }

    @Test
    @DisplayName("imza anahtarı yoksa veya 32 karakterden kısaysa uygulama açılmaz")
    void shortOrMissingSigningKeyIsRejected() {
        assertThatThrownBy(() -> new MediaProperties(null, "u", "a", "s", "b"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("MEDIA_SIGNING_KEY");
        assertThatThrownBy(() -> new MediaProperties("kisa-anahtar", "u", "a", "s", "b"))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    @DisplayName("ayarlar yazdırıldığında imza anahtarı ve şifre görünmez")
    void secretsAreHiddenInToString() {
        MediaProperties properties =
                new MediaProperties(TestMediaUrls.SIGNING_KEY, "http://minio:9000", "news-api", "gizli-sifre", "media");

        assertThat(properties.toString()).doesNotContain(TestMediaUrls.SIGNING_KEY, "gizli-sifre");
    }
}
