package com.erdemgural.newssearch.identity;

import static org.assertj.core.api.Assertions.assertThat;

import com.erdemgural.newssearch.TestDatabaseConfiguration;
import com.erdemgural.newssearch.TestElasticsearchConfiguration;
import com.erdemgural.newssearch.TestKeycloakConfiguration;
import com.erdemgural.newssearch.TestStorageConfiguration;
import com.erdemgural.newssearch.TestTokenIssuer;
import com.erdemgural.newssearch.TestUsers;
import com.erdemgural.newssearch.TestUsers.TestUser;
import java.util.List;
import java.util.Map;
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
import tools.jackson.databind.json.JsonMapper;

/**
 * API'nin yazdığı audit kayıtları (ADR-0016; FG-AL-01, 02, 04, 05): kullanıcı kaydının oluşturulması,
 * yeni oturum ve reddedilen istekler. Kayıtlar gerçek PostgreSQL'deki {@code audit_events} tablosundan
 * okunur.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import({
    TestDatabaseConfiguration.class,
    TestKeycloakConfiguration.class,
    TestElasticsearchConfiguration.class,
    TestStorageConfiguration.class
})
class AuditEventTests {

    /** Okunan bir audit kaydı; {@code whole} satırın bütün sütunlarının JSON metnidir. */
    record Event(
            String action,
            String actorType,
            UUID actorUserId,
            String targetType,
            UUID targetId,
            String result,
            String requestId,
            String ipAddress,
            Map<String, Object> details,
            String whole) {}

    private final MockMvcTester mvc;
    private final TestTokenIssuer tokenIssuer;
    private final TestUsers users;
    private final JdbcClient jdbcClient;
    private final JsonMapper jsonMapper = JsonMapper.builder().build();

    @Autowired
    AuditEventTests(MockMvcTester mvc, TestTokenIssuer tokenIssuer, TestUsers users, JdbcClient jdbcClient) {
        this.mvc = mvc;
        this.tokenIssuer = tokenIssuer;
        this.users = users;
        this.jdbcClient = jdbcClient;
    }

    private MvcTestResult get(String uri, String token) {
        return mvc.get()
                .uri(uri)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
                .exchange();
    }

    private UUID userId(String keycloakSub) {
        return jdbcClient
                .sql("SELECT id FROM users WHERE keycloak_sub = :sub")
                .param("sub", keycloakSub)
                .query(UUID.class)
                .single();
    }

    /** Kullanıcının yaptığı işlemlerin kayıtları, yazılma sırasıyla. */
    private List<Event> eventsOf(UUID actorUserId) {
        return jdbcClient
                .sql("""
				SELECT action, actor_type, actor_user_id, target_type, target_id, result, request_id,
				       host(ip_address) AS ip_address, details::text AS details, row_to_json(e)::text AS whole
				FROM audit_events e
				WHERE actor_user_id = :actorUserId
				ORDER BY occurred_at, id
				""")
                .param("actorUserId", actorUserId)
                .query((row, rowNumber) -> new Event(
                        row.getString("action"),
                        row.getString("actor_type"),
                        row.getObject("actor_user_id", UUID.class),
                        row.getString("target_type"),
                        row.getObject("target_id", UUID.class),
                        row.getString("result"),
                        row.getString("request_id"),
                        row.getString("ip_address"),
                        row.getString("details") == null
                                ? null
                                : jsonMapper.readValue(row.getString("details"), Map.class),
                        row.getString("whole")))
                .list();
    }

    private List<String> actionsOf(UUID actorUserId) {
        return eventsOf(actorUserId).stream().map(Event::action).toList();
    }

    @Test
    @DisplayName("ilk istekte kullanıcı kaydının oluşturulması bütün alanlarıyla yazılır (FG-AL-02)")
    void firstRequestRecordsUserRegistration() {
        String sub = UUID.randomUUID().toString();

        MvcTestResult result = get("/api/v1/me", tokenIssuer.token(claims -> claims.subject(sub)));

        assertThat(result).hasStatusOk();
        UUID userId = userId(sub);
        List<Event> events = eventsOf(userId);
        // Token'da oturum kimliği (sid) olmadığı için yeni oturum kaydı yoktur.
        assertThat(events).extracting(Event::action).containsExactly("USER_REGISTERED");
        Event event = events.getFirst();
        assertThat(event.actorType()).isEqualTo("USER");
        assertThat(event.actorUserId()).isEqualTo(userId);
        assertThat(event.targetType()).isEqualTo("USER");
        assertThat(event.targetId()).isEqualTo(userId);
        assertThat(event.result()).isEqualTo("SUCCESS");
        // Audit kaydı, yanıttaki istek kimliğiyle uygulama loglarına bağlanır.
        assertThat(event.requestId()).isEqualTo(result.getResponse().getHeader("X-Request-Id"));
        assertThat(event.ipAddress()).isEqualTo("127.0.0.1");
        assertThat(event.details()).containsOnly(Map.entry("role", "USER"), Map.entry("status", "PENDING"));
    }

    @Test
    @DisplayName("kayıtlı kullanıcının sonraki isteklerinde kullanıcı kaydı yeniden yazılmaz")
    void laterRequestsDoNotRecordRegistrationAgain() {
        String sub = UUID.randomUUID().toString();
        String token = tokenIssuer.token(claims -> claims.subject(sub));

        get("/api/v1/me", token);
        get("/api/v1/me", token);

        assertThat(actionsOf(userId(sub))).containsExactly("USER_REGISTERED");
    }

    @Test
    @DisplayName("yeni oturum bir kez yazılır; aynı oturumun sonraki istekleri yeni kayıt üretmez")
    void newSessionIsRecordedOnce() {
        String sub = UUID.randomUUID().toString();
        String firstSession = tokenIssuer.token(claims -> claims.subject(sub).claim("sid", "oturum-1"));
        String secondSession = tokenIssuer.token(claims -> claims.subject(sub).claim("sid", "oturum-2"));

        get("/api/v1/me", firstSession);
        get("/api/v1/me", firstSession);
        get("/api/v1/me", secondSession);

        UUID userId = userId(sub);
        assertThat(actionsOf(userId)).containsExactly("USER_REGISTERED", "SESSION_STARTED", "SESSION_STARTED");
        assertThat(eventsOf(userId).get(1).targetId()).isEqualTo(userId);
    }

    @Test
    @DisplayName("onay bekleyen kullanıcının reddedilen isteği yazılır; arama ifadesi kayda girmez (FG-AL-05)")
    void accessDeniedIsRecordedWithoutQueryString() {
        TestUser pending = users.create(UserRole.USER, UserStatus.PENDING);

        MvcTestResult result = get("/api/v1/articles?q=gizli-arama-ifadesi&sources=TRT", pending.token());

        assertThat(result).hasStatus(HttpStatus.FORBIDDEN);
        List<Event> events = eventsOf(userId(pending.keycloakSub()));
        assertThat(events).extracting(Event::action).containsExactly("ACCESS_DENIED");
        Event event = events.getFirst();
        assertThat(event.result()).isEqualTo("FAILURE");
        assertThat(event.targetType()).isNull();
        assertThat(event.targetId()).isNull();
        assertThat(event.requestId()).isEqualTo(result.getResponse().getHeader("X-Request-Id"));
        assertThat(event.details())
                .containsOnly(
                        Map.entry("method", "GET"),
                        Map.entry("path", "/api/v1/articles"),
                        Map.entry("code", "USER_PENDING_APPROVAL"));
        assertThat(event.whole()).doesNotContain("gizli-arama-ifadesi");
    }

    @Test
    @DisplayName("rolü yetmeyen aktif kullanıcının reddedilen isteği FORBIDDEN koduyla yazılır")
    void forbiddenRequestOfActiveUserIsRecorded() {
        TestUser user = users.create(UserRole.USER, UserStatus.ACTIVE);

        assertThat(get("/api/v1/admin/users", user.token())).hasStatus(HttpStatus.FORBIDDEN);

        List<Event> events = eventsOf(userId(user.keycloakSub()));
        assertThat(events).extracting(Event::action).containsExactly("ACCESS_DENIED");
        assertThat(events.getFirst().details())
                .containsEntry("path", "/api/v1/admin/users")
                .containsEntry("code", "FORBIDDEN");
    }

    @Test
    @DisplayName("kimliği doğrulanamayan istek (401) audit log'a yazılmaz")
    void unauthenticatedRequestIsNotRecorded() {
        MvcTestResult withoutToken = mvc.get().uri("/api/v1/me").exchange();
        MvcTestResult unknownKey = get("/api/v1/me", tokenIssuer.tokenSignedWithUnknownKey());

        assertThat(withoutToken).hasStatus(HttpStatus.UNAUTHORIZED);
        assertThat(unknownKey).hasStatus(HttpStatus.UNAUTHORIZED);
        for (MvcTestResult result : List.of(withoutToken, unknownKey)) {
            assertThat(jdbcClient
                            .sql("SELECT count(*) FROM audit_events WHERE request_id = :requestId")
                            .param("requestId", result.getResponse().getHeader("X-Request-Id"))
                            .query(Long.class)
                            .single())
                    .isZero();
        }
    }

    @Test
    @DisplayName("audit kayıtlarında token ve oturum kimliği bulunmaz (FG-AL-04)")
    void auditEventsContainNoTokenOrSessionId() {
        String sub = UUID.randomUUID().toString();
        String token = tokenIssuer.token(claims -> claims.subject(sub).claim("sid", "gizli-oturum-kimligi"));

        get("/api/v1/me", token);
        get("/api/v1/admin/users", token);

        List<Event> events = eventsOf(userId(sub));
        assertThat(events)
                .extracting(Event::action)
                .containsExactly("USER_REGISTERED", "SESSION_STARTED", "ACCESS_DENIED");
        assertThat(events)
                .extracting(Event::whole)
                .allSatisfy(whole -> assertThat(whole).doesNotContain(token).doesNotContain("gizli-oturum-kimligi"));
    }
}
