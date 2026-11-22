package com.erdemgural.newssearch.admin;

import static org.assertj.core.api.Assertions.assertThat;

import com.erdemgural.newssearch.TestArticles;
import com.erdemgural.newssearch.TestArticles.Article;
import com.erdemgural.newssearch.TestDatabaseConfiguration;
import com.erdemgural.newssearch.TestElasticsearchConfiguration;
import com.erdemgural.newssearch.TestKeycloakConfiguration;
import com.erdemgural.newssearch.TestStorageConfiguration;
import com.erdemgural.newssearch.TestUsers;
import com.erdemgural.newssearch.TestUsers.TestUser;
import com.erdemgural.newssearch.identity.UserRole;
import com.erdemgural.newssearch.identity.UserStatus;
import java.util.Arrays;
import java.util.List;
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

/**
 * Haber gizleme ve gizlemeyi geri alma (API sözleşmesi 6.6; FG-YP-09, FG-AR-09). Gerçek PostgreSQL ve
 * Elasticsearch ile.
 *
 * <p>Belgenin {@code hidden} alanını işçi günceller; burada çalışmaz. Arama, PostgreSQL'de gizlenmiş ama belgesi
 * henüz güncellenmemiş haberi de sonuçtan çıkarır (veri modeli 5.5); gizlenen haber bu yüzden hemen kaybolur.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import({
    TestDatabaseConfiguration.class,
    TestKeycloakConfiguration.class,
    TestElasticsearchConfiguration.class,
    TestStorageConfiguration.class
})
class ArticleModerationTests {

    private static final String ARTICLES = "/api/v1/admin/articles";

    private final MockMvcTester mvc;
    private final TestUsers users;
    private final TestArticles articles;
    private final JdbcClient jdbcClient;

    private TestUser admin;
    private UUID adminId;
    private TestUser reader;

    @Autowired
    ArticleModerationTests(MockMvcTester mvc, TestUsers users, TestArticles articles, JdbcClient jdbcClient) {
        this.mvc = mvc;
        this.users = users;
        this.articles = articles;
        this.jdbcClient = jdbcClient;
    }

    @BeforeEach
    void setUp() {
        articles.clear();
        admin = users.create(UserRole.ADMIN, UserStatus.ACTIVE);
        adminId = jdbcClient
                .sql("SELECT id FROM users WHERE keycloak_sub = :sub")
                .param("sub", admin.keycloakSub())
                .query(UUID.class)
                .single();
        reader = users.create(UserRole.USER, UserStatus.ACTIVE);
    }

    // --- Yardımcılar --------------------------------------------------------------------------------

    private MvcTestResult hide(UUID articleId, String json) {
        return mvc.post()
                .uri(ARTICLES + "/" + articleId + "/hide")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + admin.token())
                .contentType(MediaType.APPLICATION_JSON)
                .content(json)
                .exchange();
    }

    private MvcTestResult hide(UUID articleId) {
        return hide(articleId, "{\"reason\": \"Yanıltıcı başlık\"}");
    }

    private MvcTestResult unhide(UUID articleId) {
        return mvc.post()
                .uri(ARTICLES + "/" + articleId + "/unhide")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + admin.token())
                .exchange();
    }

    private MvcTestResult get(String uri, TestUser user) {
        return mvc.get()
                .uri(uri)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + user.token())
                .exchange();
    }

    /** Okurun aramasında bulunan haberlerin kimlikleri. */
    private List<String> searchIds(String query) {
        MvcTestResult result = mvc.get()
                .uri("/api/v1/articles")
                .param("q", query)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + reader.token())
                .exchange();
        assertThat(result).hasStatusOk();
        Object[] ids = assertThat(result)
                .bodyJson()
                .extractingPath("$.items[*].id")
                .asArray()
                .actual();
        return Arrays.stream(ids).map(Object::toString).toList();
    }

    private long outboxNotes(UUID articleId) {
        return jdbcClient
                .sql("""
				SELECT count(*) FROM outbox_events
				WHERE article_id = :articleId AND operation = 'INDEX' AND status = 'PENDING' AND payload IS NULL
				""")
                .param("articleId", articleId)
                .query(Long.class)
                .single();
    }

    /** Yöneticinin bu haber için yazdığı audit kayıtları: işlem, sonuç ve ayrıntı. */
    private List<String> auditOf(UUID articleId) {
        return jdbcClient
                .sql("""
				SELECT action || ' ' || result || ' ' || coalesce(details::text, '') FROM audit_events
				WHERE actor_user_id = :adminId AND target_type = 'ARTICLE' AND target_id = :articleId
				ORDER BY occurred_at, id
				""")
                .param("adminId", adminId)
                .param("articleId", articleId)
                .query(String.class)
                .list();
    }

    // --- Gizleme ve geri alma ---------------------------------------------------------------------------

    @Test
    @DisplayName("gizlenen haber aramada ve detayda görünmez; outbox notu ve audit kaydı yazılır (FG-YP-09, FG-AR-09)")
    void hiddenArticleDisappearsFromSearchAndDetail() {
        UUID id = articles.add(Article.turkish("Zeytinlikte yangın çıktı"));
        assertThat(searchIds("zeytinlik")).containsExactly(id.toString());

        MvcTestResult result = hide(id);

        assertThat(result).hasStatusOk();
        assertThat(result)
                .bodyJson()
                .extractingPath("$")
                .asMap()
                .containsEntry("hidden", true)
                .containsEntry("hiddenReason", "Yanıltıcı başlık")
                .containsEntry("hiddenBy", adminId.toString())
                .containsEntry("hiddenByEmail", admin.keycloakSub() + "@example.test");
        assertThat(searchIds("zeytinlik")).isEmpty();
        assertThat(get("/api/v1/articles/" + id, reader)).hasStatus(HttpStatus.NOT_FOUND);
        assertThat(outboxNotes(id)).isEqualTo(1);
        assertThat(auditOf(id)).containsExactly("ARTICLE_HIDDEN SUCCESS {\"reason\": \"Yanıltıcı başlık\"}");
    }

    @Test
    @DisplayName("gizleme geri alınınca haber aramada ve detayda yeniden görünür")
    void unhiddenArticleComesBack() {
        UUID id = articles.add(Article.turkish("Zeytinlikte hasat başladı"));
        assertThat(hide(id)).hasStatusOk();

        MvcTestResult result = unhide(id);

        assertThat(result).hasStatusOk();
        assertThat(result)
                .bodyJson()
                .extractingPath("$")
                .asMap()
                .containsEntry("hidden", false)
                .containsEntry("hiddenReason", null)
                .containsEntry("hiddenBy", null);
        assertThat(searchIds("zeytinlik")).containsExactly(id.toString());
        assertThat(get("/api/v1/articles/" + id, reader)).hasStatusOk();
        assertThat(outboxNotes(id)).isEqualTo(2);
        assertThat(auditOf(id)).last().isEqualTo("ARTICLE_UNHIDDEN SUCCESS ");
    }

    @Test
    @DisplayName("gizli haberi gizleme ve görünen haberi geri alma 409 alır; deneme audit'e yazılır")
    void wrongStateIsRejected() {
        UUID id = articles.add(Article.turkish("Belediye meclisi toplandı"));
        assertThat(unhide(id)).hasStatus(HttpStatus.CONFLICT);
        assertThat(hide(id)).hasStatusOk();

        MvcTestResult again = hide(id);

        assertThat(again).hasStatus(HttpStatus.CONFLICT);
        assertThat(again).bodyJson().extractingPath("$.code").isEqualTo("INVALID_STATE_TRANSITION");
        assertThat(outboxNotes(id)).isEqualTo(1);
        assertThat(auditOf(id))
                .containsExactly(
                        "ARTICLE_UNHIDDEN FAILURE {\"code\": \"INVALID_STATE_TRANSITION\"}",
                        "ARTICLE_HIDDEN SUCCESS {\"reason\": \"Yanıltıcı başlık\"}",
                        "ARTICLE_HIDDEN FAILURE {\"code\": \"INVALID_STATE_TRANSITION\"}");
    }

    @Test
    @DisplayName("gerekçe zorunludur ve en fazla 500 karakterdir; girdi hatası audit'e yazılmaz")
    void reasonIsRequired() {
        UUID id = articles.add(Article.turkish("Kütüphane yeniden açıldı"));

        for (String json : List.of("{}", "{\"reason\": \"   \"}", "{\"reason\": \"%s\"}".formatted("a".repeat(501)))) {
            MvcTestResult result = hide(id, json);
            assertThat(result).hasStatus(HttpStatus.BAD_REQUEST);
            assertThat(result).bodyJson().extractingPath("$.errors[0].field").isEqualTo("reason");
        }
        assertThat(get("/api/v1/articles/" + id, reader)).hasStatusOk();
        assertThat(auditOf(id)).isEmpty();
    }

    @Test
    @DisplayName("olmayan haber 404 alır")
    void unknownArticleIsNotFound() {
        assertThat(hide(UUID.randomUUID())).hasStatus(HttpStatus.NOT_FOUND);
        assertThat(unhide(UUID.randomUUID())).hasStatus(HttpStatus.NOT_FOUND);
    }

    // --- Liste ---------------------------------------------------------------------------------------

    @Test
    @DisplayName("gizli haberler en son gizlenen önce, gizleyenin e-postasıyla listelenir; kaynağa göre süzülür")
    void hiddenArticlesAreListed() {
        UUID first = articles.add(Article.turkish("Sahil temizlendi"));
        UUID second = articles.add(Article.english("Coastal clean-up finished"));
        articles.add(Article.turkish("Görünen haber"));
        assertThat(hide(first)).hasStatusOk();
        assertThat(hide(second)).hasStatusOk();

        MvcTestResult all = get(ARTICLES + "?hidden=true", admin);
        MvcTestResult english = get(ARTICLES + "?hidden=true&sources=GLOBALVOICES", admin);

        assertThat(all)
                .bodyJson()
                .extractingPath("$.items[*].id")
                .asArray()
                .containsExactly(second.toString(), first.toString());
        assertThat(all)
                .bodyJson()
                .extractingPath("$.items[0].hiddenByEmail")
                .isEqualTo(admin.keycloakSub() + "@example.test");
        assertThat(all).bodyJson().extractingPath("$.items[0].sourceName").isEqualTo("Global Voices");
        assertThat(english).bodyJson().extractingPath("$.items[*].id").asArray().containsExactly(second.toString());
    }

    @Test
    @DisplayName("geçersiz liste parametreleri birlikte bildirilir")
    void invalidListParametersAreRejected() {
        MvcTestResult result = get(ARTICLES + "?hidden=evet&from=dun&page=-1", admin);

        assertThat(result).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(result)
                .bodyJson()
                .extractingPath("$.errors[*].field")
                .asArray()
                .containsExactlyInAnyOrder("hidden", "from", "page");
    }

    @Test
    @DisplayName("yönetici olmayan kullanıcı haber listesini göremez ve haber gizleyemez")
    void regularUserIsForbidden() {
        UUID id = articles.add(Article.turkish("Yeni park açıldı"));

        assertThat(get(ARTICLES, reader)).hasStatus(HttpStatus.FORBIDDEN);
        assertThat(mvc.post()
                        .uri(ARTICLES + "/" + id + "/hide")
                        .header(HttpHeaders.AUTHORIZATION, "Bearer " + reader.token())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"reason\": \"x\"}")
                        .exchange())
                .hasStatus(HttpStatus.FORBIDDEN);
    }
}
