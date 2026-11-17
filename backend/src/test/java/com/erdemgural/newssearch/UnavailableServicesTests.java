package com.erdemgural.newssearch;

import static org.assertj.core.api.Assertions.assertThat;

import com.erdemgural.newssearch.TestUsers.TestUser;
import com.erdemgural.newssearch.identity.UserRole;
import com.erdemgural.newssearch.identity.UserStatus;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.assertj.MvcTestResult;

/**
 * Elasticsearch'e veya nesne depolamaya (MinIO) ulaşılamadığında uygulamanın geri kalanı çalışmaya
 * devam eder (FOG-09). Bu testte iki konteyner de yoktur; adresleri kimsenin dinlemediği bir porttur.
 */
@SpringBootTest(
        properties = {
            "ES_URL=http://127.0.0.1:9",
            "ES_PASSWORD=kullanilmiyor",
            "MINIO_URL=http://127.0.0.1:9",
            "MINIO_SECRET_KEY=kullanilmiyor",
            "MEDIA_SIGNING_KEY=" + TestMediaUrls.SIGNING_KEY
        })
@AutoConfigureMockMvc
@Import({TestDatabaseConfiguration.class, TestKeycloakConfiguration.class})
class UnavailableServicesTests {

    private final MockMvcTester mvc;
    private final TestUsers users;
    private final JdbcClient jdbcClient;

    @Autowired
    UnavailableServicesTests(MockMvcTester mvc, TestUsers users, JdbcClient jdbcClient) {
        this.mvc = mvc;
        this.users = users;
        this.jdbcClient = jdbcClient;
    }

    @Test
    @DisplayName("Elasticsearch ve MinIO kapalıyken uygulama açılır ve Kubernetes'in sağlık kontrolleri geçer")
    void probesStayHealthyWithoutBackingServices() {
        // Kontroller geçmeseydi Kubernetes pod'u yeniden başlatır veya istek göndermeyi keserdi;
        // bir yardımcı servisin kapalı olması onunla ilgisi olmayan işlevleri de durdurmuş olurdu.
        assertThat(mvc.get().uri("/actuator/health/liveness")).hasStatusOk();
        assertThat(mvc.get().uri("/actuator/health/readiness")).hasStatusOk();
    }

    @Test
    @DisplayName("Elasticsearch ve MinIO kapalıyken onlarla ilgisi olmayan uç noktalar çalışır")
    void otherEndpointsWorkWithoutBackingServices() {
        TestUser user = users.create(UserRole.USER, UserStatus.ACTIVE);

        assertThat(mvc.get()
                        .uri("/api/v1/sources")
                        .header(HttpHeaders.AUTHORIZATION, "Bearer " + user.token())
                        .exchange())
                .hasStatusOk();
    }

    @Test
    @DisplayName("Elasticsearch kapalıyken arama 503 ve SEARCH_UNAVAILABLE döner; iç ayrıntı vermez")
    void searchReportsThatItIsUnavailable() {
        TestUser user = users.create(UserRole.USER, UserStatus.ACTIVE);

        MvcTestResult result = mvc.get()
                .uri("/api/v1/articles")
                .param("q", "deprem")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + user.token())
                .exchange();

        assertThat(result).hasStatus(HttpStatus.SERVICE_UNAVAILABLE);
        assertThat(result).hasContentType("application/problem+json");
        assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("SEARCH_UNAVAILABLE");
        assertThat(result).bodyText().doesNotContain("Connection", "127.0.0.1", "Exception");
    }

    @Test
    @DisplayName("MinIO kapalıyken görsel 503 ve MEDIA_UNAVAILABLE döner; iç ayrıntı vermez")
    void mediaReportsThatItIsUnavailable() {
        UUID mediaId = insertDownloadedMedia();

        MvcTestResult result = mvc.get()
                .uri(TestMediaUrls.signedPath(mediaId, Instant.now().plusSeconds(3600)))
                .exchange();

        assertThat(result).hasStatus(HttpStatus.SERVICE_UNAVAILABLE);
        assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("MEDIA_UNAVAILABLE");
        assertThat(result).bodyText().doesNotContain("127.0.0.1", "Exception", "articles/");
    }

    /** İndirilmiş görünen bir görsel satırı (dosyanın kendisine ulaşılamayacak). */
    private UUID insertDownloadedMedia() {
        UUID articleId = jdbcClient
                .sql("""
				INSERT INTO articles (source_id, external_id, url, normalized_url, title, language, item_type,
				                      published_at, fetched_at, lifecycle_state)
				SELECT id, :key, :url, :url, 'Görselli haber', 'tr', 'ARTICLE', now(), now(), 'HOT'
				FROM sources WHERE code = 'TRT'
				RETURNING id
				""")
                .param("key", UUID.randomUUID().toString())
                .param("url", "https://example.test/" + UUID.randomUUID())
                .query(UUID.class)
                .single();
        return jdbcClient
                .sql("""
				INSERT INTO media (article_id, media_type, position, source_url, status, storage_key,
				                   content_type, size_bytes, width, height)
				VALUES (:articleId, 'IMAGE', 0, 'https://images.example.test/a.png', 'DOWNLOADED',
				        'articles/' || :articleId || '/x', 'image/png', 10, 4, 3)
				RETURNING id
				""")
                .param("articleId", articleId)
                .query(UUID.class)
                .single();
    }
}
