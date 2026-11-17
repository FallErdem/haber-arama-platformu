package com.erdemgural.newssearch.ingestion;

import static org.assertj.core.api.Assertions.assertThat;

import com.erdemgural.newssearch.TestArticles;
import com.erdemgural.newssearch.TestArticles.Article;
import com.erdemgural.newssearch.TestDatabaseConfiguration;
import com.erdemgural.newssearch.TestElasticsearchConfiguration;
import com.erdemgural.newssearch.TestImages;
import com.erdemgural.newssearch.TestKeycloakConfiguration;
import com.erdemgural.newssearch.TestMediaUrls;
import com.erdemgural.newssearch.TestStorageConfiguration;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.assertj.MvcTestResult;

/**
 * {@code GET /api/v1/media/{id}} (API sözleşmesi 4.4): görsel, MinIO'dan imzalı ve süreli adresle
 * sunulur. Gerçek PostgreSQL ve gerçek MinIO; uygulama MinIO'ya yalnızca okuma yetkisi olan
 * {@code news-api} kullanıcısıyla bağlanır.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import({
    TestDatabaseConfiguration.class,
    TestKeycloakConfiguration.class,
    TestElasticsearchConfiguration.class,
    TestStorageConfiguration.class
})
class MediaEndpointTests {

    private final MockMvcTester mvc;
    private final TestArticles articles;
    private final TestImages images;

    private UUID articleId;

    @Autowired
    MediaEndpointTests(MockMvcTester mvc, TestArticles articles, TestImages images) {
        this.mvc = mvc;
        this.articles = articles;
        this.images = images;
    }

    @BeforeEach
    void startWithOneArticle() {
        articles.clear();
        images.clearFiles();
        articleId = articles.insertRow(Article.turkish("Görselli haber"));
    }

    private static String validPath(UUID mediaId) {
        return TestMediaUrls.signedPath(
                mediaId, Instant.now().truncatedTo(ChronoUnit.HOURS).plusSeconds(7200));
    }

    @Test
    @DisplayName("imzalı adresle görsel token olmadan, doğrulanmış türüyle döner")
    void signedUrlReturnsTheImageWithoutToken() {
        byte[] body = TestImages.png(30, 20);
        UUID mediaId = images.addDownloaded(articleId, 0, body, "image/png", 30, 20);

        MvcTestResult result = mvc.get().uri(validPath(mediaId)).exchange();

        assertThat(result).hasStatusOk();
        assertThat(result).hasContentType("image/png");
        assertThat(result.getResponse().getContentAsByteArray()).isEqualTo(body);
        assertThat(result).hasHeader("X-Content-Type-Options", "nosniff");
    }

    @Test
    @DisplayName("önbellek süresi adresin kalan geçerlilik süresini aşmaz ve yalnızca tarayıcıda saklanır")
    void cacheLifetimeDoesNotOutliveTheUrl() {
        UUID mediaId = images.addDownloaded(articleId, 0, TestImages.png(4, 3), "image/png", 4, 3);
        Instant expiresAt = Instant.now().plusSeconds(600);

        MvcTestResult result =
                mvc.get().uri(TestMediaUrls.signedPath(mediaId, expiresAt)).exchange();

        String cacheControl = result.getResponse().getHeader(HttpHeaders.CACHE_CONTROL);
        assertThat(cacheControl).contains("private");
        long maxAge = Long.parseLong(cacheControl.replaceAll(".*max-age=(\\d+).*", "$1"));
        assertThat(maxAge).isBetween(590L, 600L);
    }

    @Test
    @DisplayName("imzası geçersiz adres 403 ve MEDIA_URL_INVALID ile reddedilir")
    void invalidSignatureIsRejected() {
        UUID mediaId = images.addDownloaded(articleId, 0, TestImages.png(4, 3), "image/png", 4, 3);
        String exp = String.valueOf(Instant.now().plusSeconds(3600).getEpochSecond());

        MvcTestResult result = mvc.get()
                .uri("/api/v1/media/" + mediaId + "?exp=" + exp + "&sig=uydurma-imza")
                .exchange();

        assertThat(result).hasStatus(HttpStatus.FORBIDDEN);
        assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("MEDIA_URL_INVALID");
    }

    @Test
    @DisplayName("süresi dolmuş veya parametresiz adres 403 ile reddedilir")
    void expiredOrUnsignedUrlIsRejected() {
        UUID mediaId = images.addDownloaded(articleId, 0, TestImages.png(4, 3), "image/png", 4, 3);

        assertThat(mvc.get().uri(TestMediaUrls.signedPath(mediaId, Instant.now().minusSeconds(1))))
                .hasStatus(HttpStatus.FORBIDDEN);
        assertThat(mvc.get().uri("/api/v1/media/" + mediaId)).hasStatus(HttpStatus.FORBIDDEN);
    }

    @Test
    @DisplayName("imza veritabanından önce denetlenir: imzasız istek görselin var olup olmadığını öğrenemez")
    void unsignedRequestCannotProbeForImages() {
        // Var olmayan bir görsel için de imzasız istek 404 değil 403 alır.
        assertThat(mvc.get().uri("/api/v1/media/" + UUID.randomUUID())).hasStatus(HttpStatus.FORBIDDEN);
    }

    @Test
    @DisplayName("henüz indirilmemiş veya indirilemeyen görsel 404 döner")
    void notDownloadedImageIsNotFound() {
        UUID pending = images.addNotDownloaded(articleId, 0, "PENDING");
        UUID failed = images.addNotDownloaded(articleId, 1, "FAILED");

        assertThat(mvc.get().uri(validPath(pending))).hasStatus(HttpStatus.NOT_FOUND);
        assertThat(mvc.get().uri(validPath(failed))).hasStatus(HttpStatus.NOT_FOUND);
    }

    @Test
    @DisplayName("gizlenen haberin görseli, imzası geçerli olsa da 404 döner (FG-AR-09)")
    void imageOfHiddenArticleIsNotFound() {
        UUID mediaId = images.addDownloaded(articleId, 0, TestImages.png(4, 3), "image/png", 4, 3);
        articles.hideRowOnly(articleId);

        MvcTestResult result = mvc.get().uri(validPath(mediaId)).exchange();

        assertThat(result).hasStatus(HttpStatus.NOT_FOUND);
        assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("NOT_FOUND");
    }

    @Test
    @DisplayName("kayıtlı olmayan görsel ve dosyası depolamada bulunmayan görsel 404 döner")
    void unknownImageOrMissingFileIsNotFound() {
        UUID withoutFile = images.addDownloadedWithoutFile(articleId, 0);

        assertThat(mvc.get().uri(validPath(UUID.randomUUID()))).hasStatus(HttpStatus.NOT_FOUND);
        assertThat(mvc.get().uri(validPath(withoutFile))).hasStatus(HttpStatus.NOT_FOUND);
    }

    @Test
    @DisplayName("token olmadan yalnızca görsel adresine erişilir; diğer adresler 401 döner")
    void onlyMediaPathIsOpenWithoutToken() {
        assertThat(mvc.get().uri("/api/v1/articles/" + articleId)).hasStatus(HttpStatus.UNAUTHORIZED);
        // Görsel adresi yalnızca GET ile ve tek bir kimlikle açıktır.
        assertThat(mvc.post().uri("/api/v1/media/" + UUID.randomUUID())).hasStatus(HttpStatus.UNAUTHORIZED);
        assertThat(mvc.get().uri("/api/v1/media/a/b")).hasStatus(HttpStatus.UNAUTHORIZED);
    }
}
