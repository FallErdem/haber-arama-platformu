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
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.Arrays;
import java.util.HashMap;
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
import tools.jackson.databind.json.JsonMapper;

/**
 * Audit kayıtlarının listesi ve CSV dışa aktarma (API sözleşmesi 6.8; FG-YP-10, FG-YP-11). Gerçek
 * PostgreSQL ile.
 *
 * <p>Audit kayıtları silinemez ve test sınıfları aynı veritabanını paylaşır. Bu yüzden her test kendi
 * kayıtlarını rastgele bir hedef kimliğiyle (ya da kendi yöneticisiyle) ekler ve yalnızca onlara bakar;
 * çok sayıda kayıt ekleyen testler, son 30 güne bakan diğer testlere karışmasın diye kayıtları 400 gün
 * öncesine yazar.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import({
    TestDatabaseConfiguration.class,
    TestKeycloakConfiguration.class,
    TestElasticsearchConfiguration.class,
    TestStorageConfiguration.class
})
class AuditEventAdminTests {

    private static final String EVENTS = "/api/v1/admin/audit-events";
    private static final String EXPORT = EVENTS + "/export";
    private static final String CSV_HEADER = "\"id\",\"occurred_at\",\"actor_type\",\"actor_user_id\",\"actor_email\","
            + "\"action\",\"target_type\",\"target_id\",\"result\",\"request_id\",\"ip_address\",\"details\"";

    private final MockMvcTester mvc;
    private final TestUsers users;
    private final JdbcClient jdbcClient;
    private final JsonMapper jsonMapper = JsonMapper.builder().build();

    private TestUser admin;
    private UUID adminId;

    @Autowired
    AuditEventAdminTests(MockMvcTester mvc, TestUsers users, JdbcClient jdbcClient) {
        this.mvc = mvc;
        this.users = users;
        this.jdbcClient = jdbcClient;
    }

    @BeforeEach
    void createAdmin() {
        admin = users.create(UserRole.ADMIN, UserStatus.ACTIVE);
        adminId = idOf(admin);
    }

    // --- Yardımcılar --------------------------------------------------------------------------------

    private UUID idOf(TestUser user) {
        return jdbcClient
                .sql("SELECT id FROM users WHERE keycloak_sub = :sub")
                .param("sub", user.keycloakSub())
                .query(UUID.class)
                .single();
    }

    private static String emailOf(TestUser user) {
        return user.keycloakSub() + "@example.test";
    }

    /** Adres parametreleri ad-değer çiftleri olarak: {@code get(EVENTS, admin, "result", "SUCCESS")}. */
    private MvcTestResult get(String path, TestUser user, String... parameters) {
        var request = mvc.get().uri(path).header(HttpHeaders.AUTHORIZATION, "Bearer " + user.token());
        for (int i = 0; i < parameters.length; i += 2) {
            request = request.param(parameters[i], parameters[i + 1]);
        }
        return request.exchange();
    }

    /**
     * Bir audit kaydı ekler; zamanı şu andan {@code ago} kadar öncedir ({@code '2 hours'}). Kullanıcı
     * verilmezse işçinin yazdığı gibi bir sistem kaydıdır.
     */
    private UUID insertEvent(
            UUID actorUserId,
            String action,
            String targetType,
            UUID targetId,
            String result,
            String ago,
            String details) {
        return jdbcClient
                .sql("""
				INSERT INTO audit_events (
				    occurred_at, actor_type, actor_user_id, action, target_type, target_id,
				    result, request_id, ip_address, details)
				VALUES (
				    now() - CAST(:ago AS interval),
				    CASE WHEN CAST(:actorUserId AS uuid) IS NULL THEN 'SYSTEM' ELSE 'USER' END,
				    :actorUserId, :action, :targetType, :targetId, :result,
				    CASE WHEN CAST(:actorUserId AS uuid) IS NULL THEN NULL ELSE 'test-request' END,
				    CASE WHEN CAST(:actorUserId AS uuid) IS NULL THEN NULL ELSE CAST('192.0.2.10' AS inet) END,
				    CAST(:details AS jsonb))
				RETURNING id
				""")
                .param("ago", ago)
                .param("actorUserId", actorUserId)
                .param("action", action)
                .param("targetType", targetType)
                .param("targetId", targetId)
                .param("result", result)
                .param("details", details)
                .query(UUID.class)
                .single();
    }

    /** Aynı hedefe, aynı zamanda (400 gün önce) çok sayıda sistem kaydı ekler. */
    private void insertManyEvents(UUID targetId, int count) {
        jdbcClient.sql("""
				INSERT INTO audit_events (occurred_at, actor_type, action, target_type, target_id, result)
				SELECT now() - interval '400 days', 'SYSTEM', 'FEED_AUTO_DISABLED', 'FEED', :targetId, 'SUCCESS'
				FROM generate_series(1, :count)
				""").param("targetId", targetId).param("count", count).update();
    }

    private static String daysAgo(int days) {
        return Instant.now().minus(Duration.ofDays(days)).toString();
    }

    private static List<String> ids(UUID... ids) {
        return Arrays.stream(ids).map(UUID::toString).toList();
    }

    /** Yöneticinin yazdığı dışa aktarma kayıtlarının ayrıntıları. */
    private List<Map<String, Object>> exportDetails() {
        return jdbcClient.sql("""
				SELECT details::text FROM audit_events
				WHERE actor_user_id = :adminId AND action = 'AUDIT_EXPORTED'
				  AND target_type IS NULL AND result = 'SUCCESS'
				""").param("adminId", adminId).query(String.class).list().stream()
                .map(json -> {
                    Map<String, Object> details = new HashMap<>();
                    jsonMapper
                            .readTree(json)
                            .properties()
                            .forEach(entry ->
                                    details.put(entry.getKey(), entry.getValue().asString()));
                    return details;
                })
                .toList();
    }

    /** CSV'nin satırları: imza baytları (BOM) çıkarılmış, satır sonları CRLF. */
    private static List<String> csvLines(MvcTestResult result) {
        String text = new String(result.getResponse().getContentAsByteArray(), StandardCharsets.UTF_8);
        assertThat(text).startsWith("﻿").endsWith("\r\n");
        return List.of(text.substring(1).split("\r\n"));
    }

    // --- Liste --------------------------------------------------------------------------------------

    @Test
    @DisplayName("kayıtlar yeniden eskiye, bütün alanları ve kullanıcının e-postasıyla, sayfalı listelenir (FG-YP-10)")
    void eventsAreListedNewestFirst() {
        UUID target = UUID.randomUUID();
        UUID older = insertEvent(adminId, "USER_APPROVED", "USER", target, "SUCCESS", "2 hours", null);
        UUID newer =
                insertEvent(adminId, "USER_ROLE_CHANGED", "USER", target, "FAILURE", "1 hour", "{\"to\": \"ADMIN\"}");

        MvcTestResult result = get(EVENTS, admin, "targetId", target.toString());

        assertThat(result).hasStatusOk();
        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[*].id")
                .asArray()
                .containsExactlyElementsOf(ids(newer, older));
        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[0]")
                .asMap()
                .containsEntry("actorType", "USER")
                .containsEntry("actorUserId", adminId.toString())
                .containsEntry("actorEmail", emailOf(admin))
                .containsEntry("action", "USER_ROLE_CHANGED")
                .containsEntry("targetType", "USER")
                .containsEntry("targetId", target.toString())
                .containsEntry("result", "FAILURE")
                .containsEntry("requestId", "test-request")
                .containsEntry("ipAddress", "192.0.2.10")
                .containsEntry("details", Map.of("to", "ADMIN"));
        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[1].details")
                .asMap()
                .isEmpty();

        MvcTestResult secondPage = get(EVENTS, admin, "targetId", target.toString(), "size", "1", "page", "1");
        assertThat(secondPage)
                .bodyJson()
                .extractingPath("$.items[*].id")
                .asArray()
                .containsExactlyElementsOf(ids(older));
        assertThat(secondPage).bodyJson().extractingPath("$.totalElements").isEqualTo(2);
        assertThat(secondPage).bodyJson().extractingPath("$.totalPages").isEqualTo(2);
    }

    @Test
    @DisplayName("işçinin yazdığı sistem kaydı kullanıcısız listelenir ve işlem koduyla aranabilir")
    void systemEventHasNoUser() {
        UUID target = UUID.randomUUID();
        UUID event = insertEvent(
                null, "FEED_AUTO_DISABLED", "FEED", target, "SUCCESS", "5 minutes", "{\"consecutive_failures\": 5}");

        MvcTestResult result = get(EVENTS, admin, "targetId", target.toString(), "action", "FEED_AUTO_DISABLED");

        assertThat(result).bodyJson().extractingPath("$.items[*].id").asArray().containsExactlyElementsOf(ids(event));
        assertThat(result).bodyJson().extractingPath("$.items[0].actorType").isEqualTo("SYSTEM");
        assertThat(result).bodyJson().extractingPath("$.items[0].actorUserId").isNull();
        assertThat(result).bodyJson().extractingPath("$.items[0].actorEmail").isNull();
        assertThat(result).bodyJson().extractingPath("$.items[0].ipAddress").isNull();
    }

    @Test
    @DisplayName("filtreler birlikte uygulanır: kullanıcı, işlem, hedef türü, hedef ve sonuç")
    void filtersAreCombined() {
        UUID target = UUID.randomUUID();
        UUID otherAdmin = idOf(users.create(UserRole.ADMIN, UserStatus.ACTIVE));
        insertEvent(adminId, "SOURCE_UPDATED", "SOURCE", target, "SUCCESS", "4 hours", null);
        UUID match = insertEvent(adminId, "SOURCE_UPDATED", "SOURCE", target, "FAILURE", "3 hours", null);
        insertEvent(adminId, "SOURCE_ENABLED", "SOURCE", target, "FAILURE", "2 hours", null);
        insertEvent(otherAdmin, "SOURCE_UPDATED", "SOURCE", target, "FAILURE", "1 hour", null);

        MvcTestResult result = get(
                EVENTS,
                admin,
                "actorUserId",
                adminId.toString(),
                "action",
                "SOURCE_UPDATED",
                "targetType",
                "SOURCE",
                "targetId",
                target.toString(),
                "result",
                "FAILURE");

        assertThat(result).bodyJson().extractingPath("$.items[*].id").asArray().containsExactlyElementsOf(ids(match));
    }

    @Test
    @DisplayName("tarih aralığı verilmezse son 30 gün; yalnızca üst sınır verilirse ondan önceki 30 gün")
    void defaultRangeIsLastThirtyDays() {
        UUID target = UUID.randomUUID();
        UUID recent = insertEvent(adminId, "USER_APPROVED", "USER", target, "SUCCESS", "29 days", null);
        UUID old = insertEvent(adminId, "USER_APPROVED", "USER", target, "SUCCESS", "31 days", null);

        assertThat(get(EVENTS, admin, "targetId", target.toString()))
                .bodyJson()
                .extractingPath("$.items[*].id")
                .asArray()
                .containsExactlyElementsOf(ids(recent));
        assertThat(get(EVENTS, admin, "targetId", target.toString(), "from", daysAgo(40)))
                .bodyJson()
                .extractingPath("$.items[*].id")
                .asArray()
                .containsExactlyElementsOf(ids(recent, old));
        assertThat(get(EVENTS, admin, "targetId", target.toString(), "to", daysAgo(30)))
                .bodyJson()
                .extractingPath("$.items[*].id")
                .asArray()
                .containsExactlyElementsOf(ids(old));
    }

    @Test
    @DisplayName("geçersiz parametrelerin hepsi birlikte bildirilir")
    void invalidParametersAreRejected() {
        MvcTestResult result = get(
                EVENTS,
                admin,
                "actorUserId",
                "kullanici",
                "action",
                "user_approved",
                "targetType",
                "HABER",
                "targetId",
                "hedef",
                "result",
                "OK",
                "from",
                "dün",
                "to",
                "2026-11-01",
                "page",
                "-1");

        assertThat(result).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("VALIDATION_FAILED");
        assertThat(result)
                .bodyJson()
                .extractingPath("$.errors[*].field")
                .asArray()
                .containsExactlyInAnyOrder(
                        "actorUserId", "action", "targetType", "targetId", "result", "from", "to", "page");
    }

    @Test
    @DisplayName("başlangıcı bitişinden sonra olan aralık reddedilir")
    void reversedRangeIsRejected() {
        MvcTestResult result = get(EVENTS, admin, "from", "2026-11-10T00:00:00Z", "to", "2026-11-01T00:00:00Z");

        assertThat(result).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(result).bodyJson().extractingPath("$.errors[0].field").isEqualTo("from");
        assertThat(result).bodyJson().extractingPath("$.errors[0].code").isEqualTo("INVALID_RANGE");
    }

    @Test
    @DisplayName("yönetici olmayan kullanıcı audit kayıtlarını göremez ve dışa aktaramaz")
    void regularUserIsForbidden() {
        TestUser user = users.create(UserRole.USER, UserStatus.ACTIVE);

        assertThat(get(EVENTS, user)).hasStatus(HttpStatus.FORBIDDEN);
        assertThat(get(EXPORT, user)).hasStatus(HttpStatus.FORBIDDEN);
    }

    // --- CSV dışa aktarma ---------------------------------------------------------------------------

    @Test
    @DisplayName("CSV imza baytlarıyla başlar, her alan tırnaklıdır, kayıtlar yeniden eskiye sıralıdır (FG-YP-11)")
    void exportWritesCsv() {
        UUID target = UUID.randomUUID();
        UUID userEvent = insertEvent(
                adminId, "FEED_UPDATED", "FEED", target, "SUCCESS", "2 hours", "{\"name\": \"Spor, \\\"Son\\\"\"}");
        UUID systemEvent = insertEvent(null, "FEED_AUTO_DISABLED", "FEED", target, "SUCCESS", "1 hour", null);

        MvcTestResult result = get(EXPORT, admin, "targetId", target.toString());

        assertThat(result).hasStatusOk();
        assertThat(result).hasContentType("text/csv;charset=UTF-8");
        assertThat(result.getResponse().getHeader(HttpHeaders.CONTENT_DISPOSITION))
                .startsWith("attachment; filename=\"audit-events-")
                .endsWith(".csv\"");
        byte[] bytes = result.getResponse().getContentAsByteArray();
        assertThat(Arrays.copyOf(bytes, 3)).containsExactly(0xEF, 0xBB, 0xBF);

        List<String> lines = csvLines(result);
        assertThat(lines).hasSize(3);
        assertThat(lines.get(0)).isEqualTo(CSV_HEADER);
        assertThat(lines.get(1))
                .startsWith("\"" + systemEvent + "\",")
                .contains("\"SYSTEM\",\"\",\"\",\"FEED_AUTO_DISABLED\",\"FEED\",\"" + target
                        + "\",\"SUCCESS\",\"\",\"\",\"\"");
        assertThat(lines.get(2))
                .startsWith("\"" + userEvent + "\",")
                .contains("\"USER\",\"" + adminId + "\",\"" + emailOf(admin) + "\",\"FEED_UPDATED\"")
                .contains("\"192.0.2.10\"")
                // details: {"name":"Spor, \"Son\""} → içteki tırnaklar ikilenir.
                .endsWith("\"{\"\"name\"\":\"\"Spor, \\\"\"Son\\\"\"\"\"}\"");
    }

    @Test
    @DisplayName("dışa aktarma audit'e yazılır; dosya kendi kaydını içermez")
    void exportIsAudited() {
        UUID target = UUID.randomUUID();
        insertEvent(null, "FEED_AUTO_DISABLED", "FEED", target, "SUCCESS", "1 hour", null);

        assertThat(get(EXPORT, admin, "targetId", target.toString(), "result", "SUCCESS"))
                .hasStatusOk();

        assertThat(exportDetails())
                .singleElement()
                .satisfies(details -> assertThat(details)
                        .containsEntry("targetId", target.toString())
                        .containsEntry("result", "SUCCESS")
                        .containsEntry("rowCount", "1")
                        .containsKeys("from", "to")
                        .doesNotContainKeys("actorUserId", "action", "targetType"));

        // Yöneticinin kendi kayıtları: yalnızca ilk dışa aktarmanınki; bu dışa aktarmanın kaydı dosyada yok.
        List<String> lines = csvLines(get(EXPORT, admin, "actorUserId", adminId.toString()));
        assertThat(lines).hasSize(2);
        assertThat(lines.get(1)).contains("\"AUDIT_EXPORTED\"");
        assertThat(exportDetails()).hasSize(2);
    }

    @Test
    @DisplayName("kayıtlar parça parça okunur; aynı anda yazılmış kayıtların hiçbiri atlanmaz veya tekrarlanmaz")
    void exportReadsAllChunks() {
        UUID target = UUID.randomUUID();
        // Aynı INSERT'teki now() hepsinde aynıdır: sıralama yalnızca kimlikle belirlenir.
        insertManyEvents(target, 2_500);

        List<String> lines = csvLines(get(EXPORT, admin, "targetId", target.toString(), "from", daysAgo(401)));

        List<String> rows = lines.subList(1, lines.size());
        assertThat(rows).hasSize(2_500);
        assertThat(rows.stream().map(row -> row.substring(0, row.indexOf(','))).distinct())
                .hasSize(2_500);
    }

    @Test
    @DisplayName("100.000'den fazla kayıt dışa aktarılmaz; reddedilen istek audit'e yazılmaz")
    void tooLargeExportIsRejected() {
        UUID target = UUID.randomUUID();
        insertManyEvents(target, 100_001);

        MvcTestResult result = get(EXPORT, admin, "targetId", target.toString(), "from", daysAgo(401));

        assertThat(result).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("EXPORT_TOO_LARGE");
        assertThat(exportDetails()).isEmpty();
    }
}
