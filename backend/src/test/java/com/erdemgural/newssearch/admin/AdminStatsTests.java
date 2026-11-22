package com.erdemgural.newssearch.admin;

import static org.assertj.core.api.Assertions.assertThat;

import com.erdemgural.newssearch.TestDatabaseConfiguration;
import com.erdemgural.newssearch.TestElasticsearchConfiguration;
import com.erdemgural.newssearch.TestKeycloakConfiguration;
import com.erdemgural.newssearch.TestStorageConfiguration;
import com.erdemgural.newssearch.TestUsers;
import com.erdemgural.newssearch.TestUsers.TestUser;
import com.erdemgural.newssearch.identity.UserRole;
import com.erdemgural.newssearch.identity.UserStatus;
import com.jayway.jsonpath.JsonPath;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
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
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.assertj.MvcTestResult;

/**
 * Yönetim panosu (API sözleşmesi 6.7; FG-YP-12). Gerçek PostgreSQL, Elasticsearch ve MinIO ile.
 *
 * <p>Test sınıfları aynı veritabanını paylaşır; sayıların mutlak değeri başka testlerin verisine bağlıdır.
 * Bu yüzden her test önce panoyu okur, kendi değişikliğini yapar ve sayının tam olarak ne kadar değiştiğine
 * bakar; sonunda değişikliğini geri alır.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import({
    TestDatabaseConfiguration.class,
    TestKeycloakConfiguration.class,
    TestElasticsearchConfiguration.class,
    TestStorageConfiguration.class
})
class AdminStatsTests {

    private static final String STATS = "/api/v1/admin/stats";

    private final MockMvcTester mvc;
    private final TestUsers users;
    private final JdbcClient jdbcClient;

    private TestUser admin;

    @Autowired
    AdminStatsTests(MockMvcTester mvc, TestUsers users, JdbcClient jdbcClient) {
        this.mvc = mvc;
        this.users = users;
        this.jdbcClient = jdbcClient;
    }

    @BeforeEach
    void createAdmin() {
        admin = users.create(UserRole.ADMIN, UserStatus.ACTIVE);
    }

    // --- Yardımcılar --------------------------------------------------------------------------------

    private MvcTestResult get(TestUser user) {
        return mvc.get()
                .uri(STATS)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + user.token())
                .exchange();
    }

    /** Panonun JSON yanıtı. */
    private String stats() {
        MvcTestResult result = get(admin);
        assertThat(result).hasStatusOk();
        return new String(result.getResponse().getContentAsByteArray(), StandardCharsets.UTF_8);
    }

    private static long number(String json, String path) {
        return JsonPath.<Number>read(json, path).longValue();
    }

    /** Bir kaynağın satırındaki sayı ({@code total} veya {@code last24h}). */
    private static long sourceNumber(String json, String code, String field) {
        List<Number> values = JsonPath.read(json, "$.articles.bySource[?(@.code == '" + code + "')]." + field);
        assertThat(values).hasSize(1);
        return values.getFirst().longValue();
    }

    private UUID insertTrtArticle(String fetchedAgo) {
        String key = UUID.randomUUID().toString();
        return jdbcClient
                .sql("""
				INSERT INTO articles (
				    source_id, external_id, url, normalized_url, title,
				    language, item_type, published_at, fetched_at, lifecycle_state)
				SELECT id, :key, :url, :url, 'Haber', 'tr', 'ARTICLE', now(),
				       now() - CAST(:fetchedAgo AS interval), 'HOT'
				FROM sources WHERE code = 'TRT'
				RETURNING id
				""")
                .param("key", key)
                .param("url", "https://example.test/pano/" + key)
                .param("fetchedAgo", fetchedAgo)
                .query(UUID.class)
                .single();
    }

    private void sql(String statement, Map<String, Object> params) {
        var spec = jdbcClient.sql(statement);
        for (var entry : params.entrySet()) {
            spec = spec.param(entry.getKey(), entry.getValue());
        }
        spec.update();
    }

    // --- Haberler -----------------------------------------------------------------------------------

    @Test
    @DisplayName("toplam, son 24 saatte toplanan ve kaynak bazında haber sayıları (FG-YP-12)")
    void articlesAreCountedInTotalRecentlyAndBySource() {
        String before = stats();
        UUID recent = insertTrtArticle("1 hour");
        UUID old = insertTrtArticle("2 days");
        try {
            String after = stats();

            assertThat(number(after, "$.articles.total") - number(before, "$.articles.total"))
                    .isEqualTo(2);
            assertThat(number(after, "$.articles.last24h") - number(before, "$.articles.last24h"))
                    .isEqualTo(1);
            assertThat(sourceNumber(after, "TRT", "total") - sourceNumber(before, "TRT", "total"))
                    .isEqualTo(2);
            assertThat(sourceNumber(after, "TRT", "last24h") - sourceNumber(before, "TRT", "last24h"))
                    .isEqualTo(1);
            // Haberi olsun olmasın bütün kaynaklar, adlarıyla ve ada göre sıralı gelir.
            List<String> codes = JsonPath.read(after, "$.articles.bySource[*].code");
            assertThat(codes).containsSubsequence("CNNTURK", "GLOBALVOICES", "NTV", "TRT");
            assertThat(JsonPath.<List<String>>read(after, "$.articles.bySource[?(@.code == 'TRT')].name"))
                    .containsExactly("TRT Haber");
        } finally {
            sql("DELETE FROM articles WHERE id IN (:ids)", Map.of("ids", List.of(recent, old)));
        }
    }

    // --- Kullanıcılar ve beslemeler ---------------------------------------------------------------------

    @Test
    @DisplayName("kullanıcılar durumlarına göre sayılır; kullanıcısı olmayan durum da yer alır")
    void usersAreCountedByStatus() {
        String before = stats();
        users.create(UserRole.USER, UserStatus.PENDING);

        String after = stats();

        assertThat(JsonPath.<Map<String, Object>>read(after, "$.users"))
                .containsOnlyKeys("PENDING", "ACTIVE", "PASSIVE", "REJECTED");
        assertThat(number(after, "$.users.PENDING") - number(before, "$.users.PENDING"))
                .isEqualTo(1);
        assertThat(number(after, "$.users.ACTIVE")).isEqualTo(number(before, "$.users.ACTIVE"));
    }

    @Test
    @DisplayName("okunan, hatalı ve kendiliğinden kapanmış besleme sayıları")
    void feedsAreCountedByHealth() {
        List<UUID> feedIds = jdbcClient.sql("""
				SELECT f.id FROM feeds f JOIN sources s ON s.id = f.source_id
				WHERE s.code = 'TRT' AND f.enabled ORDER BY f.name LIMIT 2
				""").query(UUID.class).list();
        UUID failing = feedIds.get(0);
        UUID autoDisabled = feedIds.get(1);
        String before = stats();
        sql("UPDATE feeds SET consecutive_failures = 2 WHERE id = :id", Map.of("id", failing));
        sql(
                "UPDATE feeds SET enabled = false, disabled_reason = 'AUTO', consecutive_failures = 5 WHERE id = :id",
                Map.of("id", autoDisabled));
        try {
            String after = stats();

            assertThat(number(after, "$.feeds.failing") - number(before, "$.feeds.failing"))
                    .isEqualTo(1);
            assertThat(number(after, "$.feeds.disabledAuto") - number(before, "$.feeds.disabledAuto"))
                    .isEqualTo(1);
            // Kapanan besleme artık okunmaz; hatalı besleme okunmaya devam eder.
            assertThat(number(before, "$.feeds.enabled") - number(after, "$.feeds.enabled"))
                    .isEqualTo(1);
        } finally {
            sql(
                    "UPDATE feeds SET enabled = true, disabled_reason = NULL, consecutive_failures = 0 WHERE id IN (:ids)",
                    Map.of("ids", feedIds));
        }
    }

    // --- Arama indeksi ve bileşenler --------------------------------------------------------------------

    @Test
    @DisplayName("Elasticsearch'e aktarılmayı bekleyen değişiklikler sayılır")
    void pendingOutboxEventsAreCounted() {
        String before = stats();
        UUID event = jdbcClient
                .sql("""
				INSERT INTO outbox_events (article_id, operation, status, next_attempt_at)
				VALUES (:articleId, 'INDEX', 'PENDING', now())
				RETURNING id
				""")
                .param("articleId", UUID.randomUUID())
                .query(UUID.class)
                .single();
        try {
            String after = stats();

            assertThat(number(after, "$.searchIndex.pendingOutboxEvents")
                            - number(before, "$.searchIndex.pendingOutboxEvents"))
                    .isEqualTo(1);
        } finally {
            sql("DELETE FROM outbox_events WHERE id = :id", Map.of("id", event));
        }
    }

    @Test
    @DisplayName("bileşenlerin durumu ve işçinin son etkinliği (en son başlatılan okuma)")
    void componentsAndWorkerActivityAreReported() {
        UUID feedId = jdbcClient
                .sql("SELECT id FROM feeds ORDER BY name LIMIT 1")
                .query(UUID.class)
                .single();
        UUID run = jdbcClient.sql("""
				INSERT INTO ingestion_runs (feed_id, trigger, status, started_at)
				VALUES (:feedId, 'SCHEDULED', 'RUNNING', TIMESTAMPTZ '2099-01-01 00:00:00+00')
				RETURNING id
				""").param("feedId", feedId).query(UUID.class).single();
        try {
            MvcTestResult result = get(admin);

            assertThat(result)
                    .bodyJson()
                    .extractingPath("$.components")
                    .asMap()
                    .containsEntry("database", "UP")
                    .containsEntry("elasticsearch", "UP")
                    .containsEntry("objectStorage", "UP")
                    .containsEntry("workerLastActivityAt", "2099-01-01T00:00:00Z");
        } finally {
            sql("DELETE FROM ingestion_runs WHERE id = :id", Map.of("id", run));
        }
    }

    @Test
    @DisplayName("yönetici olmayan kullanıcı panoyu göremez")
    void regularUserIsForbidden() {
        assertThat(get(users.create(UserRole.USER, UserStatus.ACTIVE))).hasStatus(HttpStatus.FORBIDDEN);
    }
}
