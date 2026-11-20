package com.erdemgural.newssearch.admin;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.tuple;

import com.erdemgural.newssearch.TestDatabaseConfiguration;
import com.erdemgural.newssearch.TestElasticsearchConfiguration;
import com.erdemgural.newssearch.TestKeycloakConfiguration;
import com.erdemgural.newssearch.TestStorageConfiguration;
import com.erdemgural.newssearch.TestUsers;
import com.erdemgural.newssearch.TestUsers.TestUser;
import com.erdemgural.newssearch.identity.UserRole;
import com.erdemgural.newssearch.identity.UserStatus;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import org.assertj.core.api.InstanceOfAssertFactories;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.assertj.MvcTestResult;
import tools.jackson.databind.json.JsonMapper;

/**
 * Kaynak ve besleme yönetimi, elle toplama ve toplama geçmişi (API sözleşmesi 6.2, 6.3, 6.5; FG-YP-04 – 08)
 * ve bu işlemlerin audit kayıtları (FG-AL-01). Gerçek PostgreSQL ile.
 *
 * <p>Testler başlangıç verisindeki kaynaklara (TRT, NTV…) dokunmaz; diğer test sınıfları onların etkin
 * olmasına güvenir. Her test kendi kaynağını rastgele bir kodla oluşturur ve test bitince siler.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import({
    TestDatabaseConfiguration.class,
    TestKeycloakConfiguration.class,
    TestElasticsearchConfiguration.class,
    TestStorageConfiguration.class
})
class SourceAdministrationTests {

    private static final String SOURCES = "/api/v1/admin/sources";

    /** Okunan bir audit kaydı. */
    record Event(String action, String targetType, UUID targetId, String result, Map<String, Object> details) {}

    private final MockMvcTester mvc;
    private final TestUsers users;
    private final JdbcClient jdbcClient;
    private final JsonMapper jsonMapper = JsonMapper.builder().build();

    private TestUser admin;
    private UUID adminId;

    @Autowired
    SourceAdministrationTests(MockMvcTester mvc, TestUsers users, JdbcClient jdbcClient) {
        this.mvc = mvc;
        this.users = users;
        this.jdbcClient = jdbcClient;
    }

    @BeforeEach
    void createAdmin() {
        admin = users.create(UserRole.ADMIN, UserStatus.ACTIVE);
        adminId = jdbcClient
                .sql("SELECT id FROM users WHERE keycloak_sub = :sub")
                .param("sub", admin.keycloakSub())
                .query(UUID.class)
                .single();
    }

    /**
     * Testin eklediği kaynakları, beslemelerini ve okuma kayıtlarını siler. Test sınıfları aynı veritabanını
     * paylaşır; etkin kalan bir test kaynağı kullanıcıların kaynak listesinde (SourceAndCategoryListTests)
     * görünürdü. Rastgele kodlar "T" + 8 onaltılık rakamdır; TRT bu kalıba uymaz.
     */
    @AfterEach
    void deleteTestSources() {
        String testSourceIds = "SELECT id FROM sources WHERE code ~ '^T[0-9A-F]{8}$'";
        jdbcClient
                .sql("DELETE FROM ingestion_runs WHERE feed_id IN (SELECT id FROM feeds WHERE source_id IN ("
                        + testSourceIds + "))")
                .update();
        jdbcClient
                .sql("DELETE FROM feeds WHERE source_id IN (" + testSourceIds + ")")
                .update();
        jdbcClient
                .sql("DELETE FROM sources WHERE id IN (" + testSourceIds + ")")
                .update();
    }

    // --- Yardımcılar --------------------------------------------------------------------------------

    private MvcTestResult send(String method, String uri, String json) {
        var request = switch (method) {
            case "POST" -> mvc.post().uri(uri);
            case "PATCH" -> mvc.patch().uri(uri);
            default -> mvc.get().uri(uri);
        };
        request = request.header(HttpHeaders.AUTHORIZATION, "Bearer " + admin.token());
        if (json != null) {
            request = request.contentType(MediaType.APPLICATION_JSON).content(json);
        }
        return request.exchange();
    }

    private MvcTestResult get(String uri) {
        return send("GET", uri, null);
    }

    /** Başlangıç verisiyle çakışmayan rastgele bir kaynak kodu ({@code TABCD1234}). */
    private static String randomCode() {
        return "T"
                + UUID.randomUUID().toString().replace("-", "").substring(0, 8).toUpperCase(Locale.ROOT);
    }

    private static String sourceJson(String code) {
        return """
				{"code": "%s", "name": "Kaynak %s", "homepageUrl": "https://%s.example.test",
				 "readerType": "RSS", "language": "tr", "requestIntervalSeconds": 5}
				""".formatted(code, code, code.toLowerCase(Locale.ROOT));
    }

    /** API ile kaynak ekler ve kimliğini döner. */
    private UUID createSource(String code) {
        MvcTestResult result = send("POST", SOURCES, sourceJson(code));
        assertThat(result).hasStatus(HttpStatus.CREATED);
        return UUID.fromString(
                assertThat(result).bodyJson().extractingPath("$.id").asString().actual());
    }

    private UUID createFeed(UUID sourceId, String name) {
        MvcTestResult result = send("POST", SOURCES + "/" + sourceId + "/feeds", """
				{"name": "%s", "url": "https://example.test/%s/%s.xml", "defaultCategoryCode": "SPORTS",
				 "useItemCategories": false, "fetchIntervalMinutes": 15}
				""".formatted(name, sourceId, name));
        assertThat(result).hasStatus(HttpStatus.CREATED);
        return UUID.fromString(
                assertThat(result).bodyJson().extractingPath("$.id").asString().actual());
    }

    /** Kaynağı API ile etkinleştirir (yeni kaynak devre dışı eklenir). */
    private void enableSource(UUID sourceId) {
        assertThat(send("PATCH", SOURCES + "/" + sourceId, "{\"enabled\": true, \"version\": 0}"))
                .hasStatusOk();
    }

    /** İşçinin yazdığı sağlık alanlarını ve okuma kayıtlarını taklit eden SQL. */
    private void sql(String statement, Map<String, Object> params) {
        var spec = jdbcClient.sql(statement);
        for (var entry : params.entrySet()) {
            spec = spec.param(entry.getKey(), entry.getValue());
        }
        spec.update();
    }

    /** Yöneticinin bu testte yazdığı audit kayıtları, yazılma sırasıyla. */
    private List<Event> adminEvents() {
        return jdbcClient
                .sql("""
				SELECT action, target_type, target_id, result, details::text AS details
				FROM audit_events
				WHERE actor_user_id = :adminId
				ORDER BY occurred_at, id
				""")
                .param("adminId", adminId)
                .query((row, rowNumber) -> new Event(
                        row.getString("action"),
                        row.getString("target_type"),
                        row.getObject("target_id", UUID.class),
                        row.getString("result"),
                        row.getString("details") == null
                                ? Map.of()
                                : jsonMapper.readValue(row.getString("details"), Map.class)))
                .list();
    }

    // --- Kaynak ekleme --------------------------------------------------------------------------------

    @Test
    @DisplayName("kaynak devre dışı olarak eklenir; ekleme audit'e yazılır (FG-YP-04)")
    void sourceIsCreatedDisabled() {
        String code = randomCode();

        MvcTestResult result = send("POST", SOURCES, sourceJson(code));

        assertThat(result).hasStatus(HttpStatus.CREATED);
        assertThat(result)
                .bodyJson()
                .extractingPath("$")
                .asMap()
                .containsEntry("code", code)
                .containsEntry("readerType", "RSS")
                .containsEntry("language", "tr")
                .containsEntry("requestIntervalSeconds", 5)
                .containsEntry("enabled", false)
                .containsEntry("version", 0)
                .containsEntry("dailyRequestLimit", null)
                .containsEntry("feedTimeZone", null);
        assertThat(result).bodyJson().extractingPath("$.feeds").asArray().isEmpty();
        UUID sourceId = UUID.fromString(
                assertThat(result).bodyJson().extractingPath("$.id").asString().actual());
        assertThat(adminEvents())
                .containsExactly(new Event("SOURCE_CREATED", "SOURCE", sourceId, "SUCCESS", Map.of("code", code)));
    }

    @Test
    @DisplayName("geçersiz kaynak alanları birlikte bildirilir: kod, adres, okuyucu türü, dil, sayı, saat dilimi")
    void invalidSourceIsRejected() {
        MvcTestResult result = send("POST", SOURCES, """
				{"code": "kucuk-harf", "name": "Ad", "homepageUrl": "ftp://example.test",
				 "readerType": "NYT_TOP_STORIES", "language": "de", "requestIntervalSeconds": "beş",
				 "feedTimeZone": "Mars/Olympus"}
				""");

        assertThat(result).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(result)
                .bodyJson()
                .extractingPath("$.errors[*].field")
                .asArray()
                .containsExactlyInAnyOrder(
                        "code", "homepageUrl", "readerType", "language", "requestIntervalSeconds", "feedTimeZone");
    }

    @Test
    @DisplayName("aynı kodla ikinci kaynak 409 ALREADY_EXISTS alır; deneme FAILURE olarak yazılır")
    void duplicateSourceCodeIsRejected() {
        String code = randomCode();
        createSource(code);

        MvcTestResult result = send("POST", SOURCES, sourceJson(code));

        assertThat(result).hasStatus(HttpStatus.CONFLICT);
        assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("ALREADY_EXISTS");
        assertThat(adminEvents())
                .last()
                .isEqualTo(new Event("SOURCE_CREATED", null, null, "FAILURE", Map.of("code", "ALREADY_EXISTS")));
    }

    // --- Kaynak düzenleme -------------------------------------------------------------------------------

    @Test
    @DisplayName("kaynak düzenlenir ve etkinleştirilir; değişen alanlar ve etkinleştirme ayrı yazılır")
    void sourceIsUpdatedAndEnabled() {
        UUID sourceId = createSource(randomCode());

        MvcTestResult result = send("PATCH", SOURCES + "/" + sourceId, """
				{"name": "Yeni ad %s", "feedTimeZone": "Europe/Istanbul", "enabled": true, "version": 0}
				""".formatted(sourceId));

        assertThat(result).hasStatusOk();
        assertThat(result)
                .bodyJson()
                .extractingPath("$")
                .asMap()
                .containsEntry("feedTimeZone", "Europe/Istanbul")
                .containsEntry("enabled", true)
                .containsEntry("version", 1);
        assertThat(adminEvents())
                .extracting(Event::action, Event::result, Event::details)
                .endsWith(
                        tuple("SOURCE_UPDATED", "SUCCESS", Map.of("fields", List.of("name", "feedTimeZone"))),
                        tuple("SOURCE_ENABLED", "SUCCESS", Map.of()));
    }

    @Test
    @DisplayName("PATCH'te null gönderilen alan boşaltılır, gönderilmeyen alan değişmez (sözleşme 2.5)")
    void nullClearsAndAbsentKeeps() {
        String code = randomCode();
        MvcTestResult created = send("POST", SOURCES, """
				{"code": "%s", "name": "Ad %s", "homepageUrl": "https://example.test", "readerType": "ATOM",
				 "language": "en", "requestIntervalSeconds": 10, "license": "CC BY", "attributionText": "Kaynak"}
				""".formatted(code, code));
        UUID sourceId = UUID.fromString(
                assertThat(created).bodyJson().extractingPath("$.id").asString().actual());

        MvcTestResult result = send("PATCH", SOURCES + "/" + sourceId, "{\"license\": null, \"version\": 0}");

        assertThat(result).bodyJson().extractingPath("$.license").isNull();
        assertThat(result).bodyJson().extractingPath("$.attributionText").isEqualTo("Kaynak");
    }

    @Test
    @DisplayName("kod, okuyucu türü ve dil değiştirilemez: 400 VALIDATION_FAILED")
    void immutableSourceFieldsAreRejected() {
        UUID sourceId = createSource(randomCode());

        MvcTestResult result =
                send("PATCH", SOURCES + "/" + sourceId, "{\"code\": \"BASKA\", \"language\": \"en\", \"version\": 0}");

        assertThat(result).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(result)
                .bodyJson()
                .extractingPath("$.errors[*].field")
                .asArray()
                .containsExactlyInAnyOrder("code", "language");
    }

    @Test
    @DisplayName("eski sürümle gelen düzenleme 409 VERSION_CONFLICT alır; deneme FAILURE olarak yazılır")
    void staleSourceVersionIsRejected() {
        UUID sourceId = createSource(randomCode());
        enableSource(sourceId);

        MvcTestResult result = send("PATCH", SOURCES + "/" + sourceId, "{\"enabled\": false, \"version\": 0}");

        assertThat(result).hasStatus(HttpStatus.CONFLICT);
        assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("VERSION_CONFLICT");
        assertThat(adminEvents())
                .last()
                .isEqualTo(new Event(
                        "SOURCE_DISABLED", "SOURCE", sourceId, "FAILURE", Map.of("code", "VERSION_CONFLICT")));
    }

    // --- Liste ve sağlık ---------------------------------------------------------------------------------

    @Test
    @DisplayName("kaynak listesi sağlık özetini gösterir: besleme sayısı, hatalı besleme sayısı, son başarılı okuma")
    void sourceListShowsHealth() {
        String code = randomCode();
        UUID sourceId = createSource(code);
        UUID failing = createFeed(sourceId, "hatali");
        UUID autoDisabled = createFeed(sourceId, "kapanmis");
        UUID healthy = createFeed(sourceId, "saglam");
        sql("UPDATE feeds SET consecutive_failures = 2 WHERE id = :id", Map.of("id", failing));
        sql(
                "UPDATE feeds SET enabled = false, disabled_reason = 'AUTO', consecutive_failures = 5 WHERE id = :id",
                Map.of("id", autoDisabled));
        sql("UPDATE feeds SET last_success_at = now() WHERE id = :id", Map.of("id", healthy));

        MvcTestResult result = get(SOURCES);

        assertThat(result).hasStatusOk();
        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[?(@.code == '" + code + "')]")
                .asArray()
                .singleElement()
                .asInstanceOf(InstanceOfAssertFactories.MAP)
                .containsEntry("feedCount", 3)
                .containsEntry("failingFeedCount", 2)
                .containsEntry("enabled", false)
                .extractingByKey("lastSuccessAt")
                .isNotNull();
    }

    @Test
    @DisplayName("kaynak detayı beslemeleri adlarına göre, sağlık alanlarıyla birlikte gösterir")
    void sourceDetailListsFeedsWithHealth() {
        UUID sourceId = createSource(randomCode());
        createFeed(sourceId, "b-besleme");
        UUID first = createFeed(sourceId, "a-besleme");
        sql(
                "UPDATE feeds SET consecutive_failures = 1, last_error = 'Zaman aşımı' WHERE id = :id",
                Map.of("id", first));

        MvcTestResult result = get(SOURCES + "/" + sourceId);

        assertThat(result)
                .bodyJson()
                .extractingPath("$.feeds[*].name")
                .asArray()
                .containsExactly("a-besleme", "b-besleme");
        assertThat(result)
                .bodyJson()
                .extractingPath("$.feeds[0]")
                .asMap()
                .containsEntry("consecutiveFailures", 1)
                .containsEntry("lastError", "Zaman aşımı")
                .containsEntry("defaultCategoryCode", "SPORTS")
                .containsEntry("enabled", true)
                .containsEntry("disabledReason", null);
        assertThat(get(SOURCES + "/" + UUID.randomUUID())).hasStatus(HttpStatus.NOT_FOUND);
    }

    // --- Beslemeler --------------------------------------------------------------------------------------

    @Test
    @DisplayName("besleme etkin eklenir ve okuma zamanı hemen gelmiştir; ekleme audit'e yazılır")
    void feedIsCreatedAndDueImmediately() {
        UUID sourceId = createSource(randomCode());

        UUID feedId = createFeed(sourceId, "spor");

        Boolean due = jdbcClient
                .sql("SELECT enabled AND next_fetch_at <= now() FROM feeds WHERE id = :id")
                .param("id", feedId)
                .query(Boolean.class)
                .single();
        assertThat(due).isTrue();
        assertThat(adminEvents())
                .last()
                .isEqualTo(new Event(
                        "FEED_CREATED",
                        "FEED",
                        feedId,
                        "SUCCESS",
                        Map.of("sourceId", sourceId.toString(), "name", "spor")));
    }

    @Test
    @DisplayName("bilinmeyen kategori 400, aynı adres 409 ALREADY_EXISTS, olmayan kaynak 404 alır")
    void invalidFeedsAreRejected() {
        UUID sourceId = createSource(randomCode());
        createFeed(sourceId, "ilk");

        MvcTestResult unknownCategory = send("POST", SOURCES + "/" + sourceId + "/feeds", """
				{"name": "x", "url": "https://example.test/x.xml", "defaultCategoryCode": "YOK",
				 "useItemCategories": true, "fetchIntervalMinutes": 15}
				""");
        MvcTestResult sameUrl = send("POST", SOURCES + "/" + sourceId + "/feeds", """
				{"name": "ikinci", "url": "https://example.test/%s/ilk.xml",
				 "useItemCategories": true, "fetchIntervalMinutes": 15}
				""".formatted(sourceId));
        MvcTestResult unknownSource = send("POST", SOURCES + "/" + UUID.randomUUID() + "/feeds", """
				{"name": "y", "url": "https://example.test/y.xml", "useItemCategories": true, "fetchIntervalMinutes": 15}
				""");

        assertThat(unknownCategory).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(unknownCategory)
                .bodyJson()
                .extractingPath("$.errors[0].field")
                .isEqualTo("defaultCategoryCode");
        assertThat(sameUrl).hasStatus(HttpStatus.CONFLICT);
        assertThat(sameUrl).bodyJson().extractingPath("$.code").isEqualTo("ALREADY_EXISTS");
        assertThat(unknownSource).hasStatus(HttpStatus.NOT_FOUND);
    }

    @Test
    @DisplayName("kendiliğinden kapanmış besleme etkinleştirilince hata sayacı sıfırlanır ve hemen okunur (FG-YP-07)")
    void autoDisabledFeedIsReenabled() {
        UUID feedId = createFeed(createSource(randomCode()), "kapanan");
        sql("""
				UPDATE feeds SET enabled = false, disabled_reason = 'AUTO', consecutive_failures = 5,
				                 next_fetch_at = now() + interval '1 hour'
				WHERE id = :id
				""", Map.of("id", feedId));

        MvcTestResult result = send("PATCH", "/api/v1/admin/feeds/" + feedId, "{\"enabled\": true, \"version\": 0}");

        assertThat(result).hasStatusOk();
        assertThat(result)
                .bodyJson()
                .extractingPath("$")
                .asMap()
                .containsEntry("enabled", true)
                .containsEntry("disabledReason", null)
                .containsEntry("consecutiveFailures", 0)
                .containsEntry("version", 1);
        Boolean due = jdbcClient
                .sql("SELECT next_fetch_at <= now() FROM feeds WHERE id = :id")
                .param("id", feedId)
                .query(Boolean.class)
                .single();
        assertThat(due).isTrue();
        assertThat(adminEvents())
                .last()
                .isEqualTo(new Event("FEED_ENABLED", "FEED", feedId, "SUCCESS", Map.of("previousReason", "AUTO")));
    }

    @Test
    @DisplayName("yöneticinin kapattığı beslemenin nedeni MANUAL olur")
    void feedIsDisabledManually() {
        UUID feedId = createFeed(createSource(randomCode()), "kapatilacak");

        MvcTestResult result = send("PATCH", "/api/v1/admin/feeds/" + feedId, "{\"enabled\": false, \"version\": 0}");

        assertThat(result).bodyJson().extractingPath("$.disabledReason").isEqualTo("MANUAL");
        assertThat(adminEvents()).last().extracting(Event::action).isEqualTo("FEED_DISABLED");
    }

    @Test
    @DisplayName("besleme adresi değişince eski adresin koşullu istek değerleri silinir")
    void changingFeedUrlClearsValidators() {
        UUID feedId = createFeed(createSource(randomCode()), "adres");
        sql("UPDATE feeds SET etag = '\"v1\"', last_modified = 'dün' WHERE id = :id", Map.of("id", feedId));

        send("PATCH", "/api/v1/admin/feeds/" + feedId, """
				{"url": "https://example.test/yeni-%s.xml", "version": 0}
				""".formatted(feedId));

        Boolean cleared = jdbcClient
                .sql("SELECT etag IS NULL AND last_modified IS NULL FROM feeds WHERE id = :id")
                .param("id", feedId)
                .query(Boolean.class)
                .single();
        assertThat(cleared).isTrue();
        assertThat(adminEvents())
                .last()
                .isEqualTo(new Event("FEED_UPDATED", "FEED", feedId, "SUCCESS", Map.of("fields", List.of("url"))));
    }

    // --- Elle toplama ------------------------------------------------------------------------------------

    @Test
    @DisplayName("elle toplama kaynağın etkin beslemelerini hemen okunacak hale getirir; kapalı beslemeye dokunmaz")
    void fetchRequestMarksEnabledFeeds() {
        UUID sourceId = createSource(randomCode());
        UUID enabled = createFeed(sourceId, "acik");
        UUID disabled = createFeed(sourceId, "kapali");
        sql("UPDATE feeds SET next_fetch_at = now() + interval '1 hour' WHERE source_id = :id", Map.of("id", sourceId));
        send("PATCH", "/api/v1/admin/feeds/" + disabled, "{\"enabled\": false, \"version\": 0}");
        enableSource(sourceId);

        MvcTestResult result = send("POST", SOURCES + "/" + sourceId + "/fetch", null);

        assertThat(result).hasStatus(HttpStatus.ACCEPTED);
        assertThat(result).bodyJson().extractingPath("$.feedCount").isEqualTo(1);
        assertThat(fetchRequested(enabled)).isTrue();
        assertThat(fetchRequested(disabled)).isFalse();
        assertThat(adminEvents())
                .last()
                .isEqualTo(new Event("FETCH_REQUESTED", "SOURCE", sourceId, "SUCCESS", Map.of("feedCount", 1)));
    }

    /** İstek yazıldı mı ve okuma zamanı şimdiye çekildi mi (işçi bunu MANUAL okuma olarak görür). */
    private boolean fetchRequested(UUID feedId) {
        return jdbcClient
                .sql(
                        "SELECT manual_fetch_requested_at IS NOT NULL AND next_fetch_at <= now() FROM feeds WHERE id = :id")
                .param("id", feedId)
                .query(Boolean.class)
                .single();
    }

    @Test
    @DisplayName("devre dışı kaynakta elle toplama 409 INVALID_STATE_TRANSITION alır; deneme yazılır")
    void fetchOnDisabledSourceIsRejected() {
        UUID sourceId = createSource(randomCode());

        MvcTestResult result = send("POST", SOURCES + "/" + sourceId + "/fetch", null);

        assertThat(result).hasStatus(HttpStatus.CONFLICT);
        assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("INVALID_STATE_TRANSITION");
        assertThat(adminEvents())
                .last()
                .isEqualTo(new Event(
                        "FETCH_REQUESTED", "SOURCE", sourceId, "FAILURE", Map.of("code", "INVALID_STATE_TRANSITION")));
    }

    // --- Toplama geçmişi ---------------------------------------------------------------------------------

    @Test
    @DisplayName("toplama geçmişi kaynağa ve duruma göre süzülür, en yeniden eskiye sıralıdır (FG-YP-05)")
    void ingestionRunsAreFilteredAndOrdered() {
        UUID sourceId = createSource(randomCode());
        UUID feedId = createFeed(sourceId, "gecmis");
        insertRun(feedId, "SCHEDULED", "SUCCEEDED", "2 hours");
        insertRun(feedId, "MANUAL", "FAILED", "1 hour");
        insertRun(feedId, "SCHEDULED", "NOT_MODIFIED", "3 hours");

        MvcTestResult all = get("/api/v1/admin/ingestion-runs?sourceId=" + sourceId);
        MvcTestResult failed = get("/api/v1/admin/ingestion-runs?sourceId=" + sourceId + "&status=FAILED");

        assertThat(all).hasStatusOk();
        assertThat(all)
                .bodyJson()
                .extractingPath("$.items[*].status")
                .asArray()
                .containsExactly("FAILED", "SUCCEEDED", "NOT_MODIFIED");
        assertThat(all)
                .bodyJson()
                .extractingPath("$.items[0]")
                .asMap()
                .containsEntry("trigger", "MANUAL")
                .containsEntry("feedName", "gecmis")
                .containsEntry("sourceId", sourceId.toString());
        assertThat(failed).bodyJson().extractingPath("$.totalElements").isEqualTo(1);
    }

    private void insertRun(UUID feedId, String trigger, String status, String ago) {
        sql("""
				INSERT INTO ingestion_runs (feed_id, trigger, status, started_at, finished_at)
				VALUES (:feedId, :trigger, :status, now() - CAST(:ago AS interval), now() - CAST(:ago AS interval))
				""", Map.of("feedId", feedId, "trigger", trigger, "status", status, "ago", ago));
    }

    @Test
    @DisplayName("geçersiz geçmiş filtreleri birlikte bildirilir: kimlik, durum, tarih aralığı")
    void invalidIngestionRunFiltersAreRejected() {
        MvcTestResult result = get("/api/v1/admin/ingestion-runs?sourceId=abc&status=OK"
                + "&from=2026-11-20T00:00:00Z&to=2026-11-19T00:00:00Z");

        assertThat(result).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(result)
                .bodyJson()
                .extractingPath("$.errors[*].field")
                .asArray()
                .containsExactlyInAnyOrder("sourceId", "status", "from");
    }

    // --- Yetki -------------------------------------------------------------------------------------------

    @Test
    @DisplayName("USER rolündeki kullanıcı kaynak yönetimi uç noktalarını kullanamaz")
    void regularUserIsForbidden() {
        TestUser user = users.create(UserRole.USER, UserStatus.ACTIVE);

        for (String uri : List.of(SOURCES, "/api/v1/admin/ingestion-runs")) {
            assertThat(mvc.get()
                            .uri(uri)
                            .header(HttpHeaders.AUTHORIZATION, "Bearer " + user.token())
                            .exchange())
                    .hasStatus(HttpStatus.FORBIDDEN);
        }
        assertThat(mvc.post()
                        .uri(SOURCES)
                        .header(HttpHeaders.AUTHORIZATION, "Bearer " + user.token())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(sourceJson(randomCode()))
                        .exchange())
                .hasStatus(HttpStatus.FORBIDDEN);
    }
}
