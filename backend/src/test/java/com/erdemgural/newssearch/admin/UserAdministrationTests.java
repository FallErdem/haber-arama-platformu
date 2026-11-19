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
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.assertj.MvcTestResult;
import tools.jackson.databind.json.JsonMapper;

/**
 * Kullanıcı yönetimi: {@code /api/v1/admin/users} (API sözleşmesi 6.1; FG-YP-01 – 03, FOG-19) ve bu
 * işlemlerin audit kayıtları (FG-AL-01). Gerçek PostgreSQL ile.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import({
    TestDatabaseConfiguration.class,
    TestKeycloakConfiguration.class,
    TestElasticsearchConfiguration.class,
    TestStorageConfiguration.class
})
class UserAdministrationTests {

    private static final String PATH = "/api/v1/admin/users";

    /** Okunan bir audit kaydı. */
    record Event(String action, UUID actorUserId, String result, Map<String, Object> details) {}

    private final MockMvcTester mvc;
    private final TestUsers users;
    private final JdbcClient jdbcClient;
    private final JsonMapper jsonMapper = JsonMapper.builder().build();

    private TestUser admin;
    private UUID adminId;

    @Autowired
    UserAdministrationTests(MockMvcTester mvc, TestUsers users, JdbcClient jdbcClient) {
        this.mvc = mvc;
        this.users = users;
        this.jdbcClient = jdbcClient;
    }

    @BeforeEach
    void createAdmin() {
        admin = users.create(UserRole.ADMIN, UserStatus.ACTIVE);
        adminId = idOf(admin);
    }

    private UUID idOf(TestUser user) {
        return jdbcClient
                .sql("SELECT id FROM users WHERE keycloak_sub = :sub")
                .param("sub", user.keycloakSub())
                .query(UUID.class)
                .single();
    }

    /** Testin kendi e-posta ve adıyla kullanıcı ekler; arama testleri için. */
    private UUID insertUser(String email, String displayName, UserRole role, UserStatus status) {
        return jdbcClient
                .sql("""
				INSERT INTO users (keycloak_sub, email, display_name, role, status)
				VALUES (:sub, :email, :displayName, :role, :status)
				RETURNING id
				""")
                .param("sub", UUID.randomUUID().toString())
                .param("email", email)
                .param("displayName", displayName)
                .param("role", role.name())
                .param("status", status.name())
                .query(UUID.class)
                .single();
    }

    /**
     * Liste isteği. Parametreler {@code param()} ile verilir: değer olduğu gibi gider ({@code %} ve Türkçe
     * harfleri MockMvc kodlar); adrese elle yazılsa {@code %} ikinci kez kodlanabilirdi.
     */
    private MvcTestResult list(String query) {
        var request = mvc.get().uri(PATH).header(HttpHeaders.AUTHORIZATION, "Bearer " + admin.token());
        for (String pair : query.split("&")) {
            if (!pair.isEmpty()) {
                String[] parts = pair.split("=", 2);
                request = request.param(parts[0], parts.length > 1 ? parts[1] : "");
            }
        }
        return request.exchange();
    }

    private String roleOf(UUID userId) {
        return jdbcClient
                .sql("SELECT role FROM users WHERE id = :id")
                .param("id", userId)
                .query(String.class)
                .single();
    }

    private MvcTestResult post(UUID userId, String operation) {
        return mvc.post()
                .uri(PATH + "/" + userId + "/" + operation)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + admin.token())
                .exchange();
    }

    private MvcTestResult patch(TestUser by, UUID userId, String json) {
        return mvc.patch()
                .uri(PATH + "/" + userId)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + by.token())
                .contentType(MediaType.APPLICATION_JSON)
                .content(json)
                .exchange();
    }

    private MvcTestResult patch(UUID userId, String json) {
        return patch(admin, userId, json);
    }

    private MvcTestResult getAs(TestUser user, String uri) {
        return mvc.get()
                .uri(uri)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + user.token())
                .exchange();
    }

    /** Kullanıcı üzerinde yapılan işlemlerin kayıtları, yazılma sırasıyla. */
    private List<Event> eventsOn(UUID userId) {
        return jdbcClient
                .sql("""
				SELECT action, actor_user_id, result, details::text AS details
				FROM audit_events
				WHERE target_type = 'USER' AND target_id = :userId AND action <> 'USER_REGISTERED'
				ORDER BY occurred_at, id
				""")
                .param("userId", userId)
                .query((row, rowNumber) -> new Event(
                        row.getString("action"),
                        row.getObject("actor_user_id", UUID.class),
                        row.getString("result"),
                        row.getString("details") == null
                                ? Map.of()
                                : jsonMapper.readValue(row.getString("details"), Map.class)))
                .list();
    }

    // --- Liste ---------------------------------------------------------------------------------------

    @Test
    @DisplayName("liste durum filtresiyle ve e-posta veya adda Türkçe harflerle büyük/küçük harf duyarsız aranır")
    void listFiltersAndSearchesCaseInsensitively() {
        String marker = UUID.randomUUID().toString().substring(0, 8);
        UUID pending = insertUser(marker + "-a@example.test", "Ahmet Şahin", UserRole.USER, UserStatus.PENDING);
        UUID active = insertUser(marker + "-b@example.test", "Ayşe ŞAHİN", UserRole.USER, UserStatus.ACTIVE);
        insertUser(marker + "-c@example.test", "Can Yılmaz", UserRole.USER, UserStatus.PENDING);

        MvcTestResult byName = list("q=" + "şahin");
        MvcTestResult byEmailAndStatus = list("q=" + marker + "&status=PENDING");

        assertThat(byName).hasStatusOk();
        assertThat(byName)
                .bodyJson()
                .extractingPath("$.items[*].id")
                .asArray()
                .contains(pending.toString(), active.toString());
        assertThat(byEmailAndStatus)
                .bodyJson()
                .extractingPath("$.totalElements")
                .isEqualTo(2);
        assertThat(byEmailAndStatus)
                .bodyJson()
                .extractingPath("$.items[*].status")
                .asArray()
                .containsOnly("PENDING");
        assertThat(byEmailAndStatus)
                .bodyJson()
                .extractingPath("$.items[0]")
                .asMap()
                .containsOnlyKeys("id", "email", "displayName", "role", "status", "createdAt", "version");
    }

    @Test
    @DisplayName("aramadaki % ve _ harfin kendisi olarak aranır, joker değildir")
    void likeWildcardsInQueryAreLiteral() {
        String marker = UUID.randomUUID().toString().substring(0, 8);
        insertUser(marker + "@example.test", "Joker Deneme", UserRole.USER, UserStatus.ACTIVE);

        // Joker olsaydı "<marker>%" bu kullanıcıyla, "<ilk dört harf>_" da onun e-postasıyla eşleşirdi.
        assertThat(list("q=" + marker))
                .bodyJson()
                .extractingPath("$.totalElements")
                .isEqualTo(1);
        assertThat(list("q=" + marker + "%"))
                .bodyJson()
                .extractingPath("$.totalElements")
                .isEqualTo(0);
        assertThat(list("q=" + marker.substring(0, 4) + "_"))
                .bodyJson()
                .extractingPath("$.totalElements")
                .isEqualTo(0);
    }

    @Test
    @DisplayName("geçersiz filtre değerleri birlikte bildirilir: 400 VALIDATION_FAILED")
    void invalidFiltersAreRejected() {
        MvcTestResult result = list("status=SILINMIS&role=ROOT&size=101");

        assertThat(result).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(result)
                .bodyJson()
                .extractingPath("$.errors[*].field")
                .asArray()
                .containsExactlyInAnyOrder("status", "role", "size");
    }

    // --- Onay ve ret ---------------------------------------------------------------------------------

    @Test
    @DisplayName("onay bekleyen kullanıcı onaylanır: aktif olur, rolü USER olur, uygulamayı kullanabilir")
    void pendingUserIsApproved() {
        TestUser pending = users.create(UserRole.USER, UserStatus.PENDING);
        UUID pendingId = idOf(pending);

        MvcTestResult result = post(pendingId, "approve");

        assertThat(result).hasStatusOk();
        assertThat(result).bodyJson().extractingPath("$.status").isEqualTo("ACTIVE");
        assertThat(result).bodyJson().extractingPath("$.role").isEqualTo("USER");
        assertThat(result).bodyJson().extractingPath("$.version").isEqualTo(1);
        assertThat(getAs(pending, "/api/v1/me/saved-articles")).hasStatusOk();
        assertThat(eventsOn(pendingId)).containsExactly(new Event("USER_APPROVED", adminId, "SUCCESS", Map.of()));
    }

    @Test
    @DisplayName("onay bekleyen kullanıcı reddedilir; sonraki isteği 403 USER_REJECTED alır")
    void pendingUserIsRejected() {
        TestUser pending = users.create(UserRole.USER, UserStatus.PENDING);
        UUID pendingId = idOf(pending);

        MvcTestResult result = post(pendingId, "reject");

        assertThat(result).hasStatusOk();
        assertThat(result).bodyJson().extractingPath("$.status").isEqualTo("REJECTED");
        assertThat(getAs(pending, "/api/v1/me/saved-articles"))
                .bodyJson()
                .extractingPath("$.code")
                .isEqualTo("USER_REJECTED");
        assertThat(eventsOn(pendingId)).containsExactly(new Event("USER_REJECTED", adminId, "SUCCESS", Map.of()));
    }

    @Test
    @DisplayName("onay bekleyen olmayan kullanıcı onaylanamaz: 409 INVALID_STATE_TRANSITION; deneme FAILURE yazılır")
    void onlyPendingUserCanBeApproved() {
        UUID activeId = idOf(users.create(UserRole.USER, UserStatus.ACTIVE));

        MvcTestResult result = post(activeId, "approve");

        assertThat(result).hasStatus(HttpStatus.CONFLICT);
        assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("INVALID_STATE_TRANSITION");
        assertThat(eventsOn(activeId))
                .containsExactly(
                        new Event("USER_APPROVED", adminId, "FAILURE", Map.of("code", "INVALID_STATE_TRANSITION")));
    }

    @Test
    @DisplayName("var olmayan kullanıcı için 404 NOT_FOUND döner ve audit kaydı yazılmaz")
    void unknownUserIsNotFound() {
        UUID unknown = UUID.randomUUID();

        assertThat(post(unknown, "approve")).hasStatus(HttpStatus.NOT_FOUND);
        assertThat(eventsOn(unknown)).isEmpty();
    }

    // --- Rol ve durum ----------------------------------------------------------------------------------

    @Test
    @DisplayName("rol ve durum değişir, sürüm artar; pasif yapılan kullanıcının sonraki isteği 403 alır (FOG-19)")
    void roleAndStatusAreChanged() {
        TestUser user = users.create(UserRole.USER, UserStatus.ACTIVE);
        UUID userId = idOf(user);

        MvcTestResult promoted = patch(userId, "{\"role\": \"ADMIN\", \"version\": 0}");
        MvcTestResult deactivated = patch(userId, "{\"status\": \"PASSIVE\", \"version\": 1}");

        assertThat(promoted).hasStatusOk();
        assertThat(promoted).bodyJson().extractingPath("$.role").isEqualTo("ADMIN");
        assertThat(promoted).bodyJson().extractingPath("$.version").isEqualTo(1);
        assertThat(deactivated).hasStatusOk();
        assertThat(deactivated).bodyJson().extractingPath("$.status").isEqualTo("PASSIVE");
        assertThat(deactivated).bodyJson().extractingPath("$.version").isEqualTo(2);
        assertThat(getAs(user, "/api/v1/me/saved-articles"))
                .bodyJson()
                .extractingPath("$.code")
                .isEqualTo("USER_PASSIVE");
        assertThat(eventsOn(userId))
                .containsExactly(
                        new Event("USER_ROLE_CHANGED", adminId, "SUCCESS", Map.of("from", "USER", "to", "ADMIN")),
                        new Event(
                                "USER_STATUS_CHANGED", adminId, "SUCCESS", Map.of("from", "ACTIVE", "to", "PASSIVE")));
    }

    @Test
    @DisplayName("eski sürümle gelen değişiklik 409 VERSION_CONFLICT ile reddedilir; kayıt değişmez")
    void staleVersionIsRejected() {
        UUID userId = idOf(users.create(UserRole.USER, UserStatus.ACTIVE));
        patch(userId, "{\"status\": \"PASSIVE\", \"version\": 0}");

        // Başka bir yönetici kaydı bu arada değiştirmiş; istemci hâlâ 0. sürümü görüyor.
        MvcTestResult result = patch(userId, "{\"role\": \"ADMIN\", \"version\": 0}");

        assertThat(result).hasStatus(HttpStatus.CONFLICT);
        assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("VERSION_CONFLICT");
        assertThat(roleOf(userId)).isEqualTo("USER");
        assertThat(eventsOn(userId))
                .last()
                .isEqualTo(new Event(
                        "USER_ROLE_CHANGED", adminId, "FAILURE", Map.of("to", "ADMIN", "code", "VERSION_CONFLICT")));
    }

    @Test
    @DisplayName("onay bekleyen kullanıcının rolü ve durumu değiştirilemez: 409 INVALID_STATE_TRANSITION")
    void pendingUserCannotBeChanged() {
        UUID pendingId = idOf(users.create(UserRole.USER, UserStatus.PENDING));

        MvcTestResult result = patch(pendingId, "{\"status\": \"ACTIVE\", \"version\": 0}");

        assertThat(result).hasStatus(HttpStatus.CONFLICT);
        assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("INVALID_STATE_TRANSITION");
    }

    @Test
    @DisplayName("son aktif yönetici kendi rolünü düşüremez ve kendini pasif yapamaz (FG-YP-03)")
    void lastActiveAdminCannotBeRemoved() {
        // Test veritabanını paylaşan diğer testlerin yöneticileri; bu testte tek aktif yönetici admin olmalı.
        jdbcClient
                .sql("UPDATE users SET status = 'PASSIVE' WHERE role = 'ADMIN' AND status = 'ACTIVE' AND id <> :id")
                .param("id", adminId)
                .update();

        MvcTestResult demote = patch(adminId, "{\"role\": \"USER\", \"version\": 0}");
        MvcTestResult deactivate = patch(adminId, "{\"status\": \"PASSIVE\", \"version\": 0}");

        assertThat(demote).hasStatus(HttpStatus.CONFLICT);
        assertThat(demote).bodyJson().extractingPath("$.code").isEqualTo("LAST_ACTIVE_ADMIN");
        assertThat(deactivate).bodyJson().extractingPath("$.code").isEqualTo("LAST_ACTIVE_ADMIN");
        assertThat(eventsOn(adminId))
                .extracting(Event::action, Event::result)
                .containsExactly(tuple("USER_ROLE_CHANGED", "FAILURE"), tuple("USER_STATUS_CHANGED", "FAILURE"));
        assertThat(roleOf(adminId)).isEqualTo("ADMIN");
    }

    @Test
    @DisplayName("başka bir aktif yönetici varken yönetici kendi rolünü düşürebilir")
    void adminCanStepDownWhenAnotherActiveAdminExists() {
        users.create(UserRole.ADMIN, UserStatus.ACTIVE);

        MvcTestResult result = patch(adminId, "{\"role\": \"USER\", \"version\": 0}");

        assertThat(result).hasStatusOk();
        assertThat(result).bodyJson().extractingPath("$.role").isEqualTo("USER");
        // Rolü düştüğü için yönetim uç noktalarına artık erişemez.
        assertThat(list("")).hasStatus(HttpStatus.FORBIDDEN);
    }

    @Test
    @DisplayName("gövdedeki geçersiz değerler birlikte bildirilir: durum yalnızca ACTIVE veya PASSIVE, sürüm zorunlu")
    void invalidChangeIsRejected() {
        UUID userId = idOf(users.create(UserRole.USER, UserStatus.ACTIVE));

        MvcTestResult result = patch(userId, "{\"role\": \"ROOT\", \"status\": \"PENDING\"}");

        assertThat(result).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("VALIDATION_FAILED");
        assertThat(result)
                .bodyJson()
                .extractingPath("$.errors[*].field")
                .asArray()
                .containsExactlyInAnyOrder("role", "status", "version");
        assertThat(patch(userId, "bozuk json")).hasStatus(HttpStatus.BAD_REQUEST);
    }

    // --- Yetki ---------------------------------------------------------------------------------------

    @Test
    @DisplayName("USER rolündeki kullanıcı kullanıcı yönetimi uç noktalarını kullanamaz")
    void regularUserIsForbidden() {
        TestUser user = users.create(UserRole.USER, UserStatus.ACTIVE);
        UUID target = idOf(users.create(UserRole.USER, UserStatus.PENDING));

        assertThat(getAs(user, PATH)).hasStatus(HttpStatus.FORBIDDEN);
        assertThat(mvc.post()
                        .uri(PATH + "/" + target + "/approve")
                        .header(HttpHeaders.AUTHORIZATION, "Bearer " + user.token())
                        .exchange())
                .hasStatus(HttpStatus.FORBIDDEN);
        assertThat(patch(user, target, "{\"role\": \"ADMIN\", \"version\": 0}")).hasStatus(HttpStatus.FORBIDDEN);
    }
}
