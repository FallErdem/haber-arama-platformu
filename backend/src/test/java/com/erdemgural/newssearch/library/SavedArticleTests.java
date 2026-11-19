package com.erdemgural.newssearch.library;

import static org.assertj.core.api.Assertions.assertThat;

import com.erdemgural.newssearch.TestArticles;
import com.erdemgural.newssearch.TestArticles.Article;
import com.erdemgural.newssearch.TestDatabaseConfiguration;
import com.erdemgural.newssearch.TestElasticsearchConfiguration;
import com.erdemgural.newssearch.TestImages;
import com.erdemgural.newssearch.TestKeycloakConfiguration;
import com.erdemgural.newssearch.TestStorageConfiguration;
import com.erdemgural.newssearch.TestUsers;
import com.erdemgural.newssearch.TestUsers.TestUser;
import com.erdemgural.newssearch.identity.UserRole;
import com.erdemgural.newssearch.identity.UserStatus;
import java.time.Instant;
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
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.assertj.MvcTestResult;

/**
 * Kaydedilen haberler: {@code GET}, {@code PUT} ve {@code DELETE /api/v1/me/saved-articles} (API sözleşmesi
 * 5.1, FG-KO-01 – 03). Gerçek PostgreSQL ile; haberlerin meta verisi {@code ingestion} modülünden gelir.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import({
    TestDatabaseConfiguration.class,
    TestKeycloakConfiguration.class,
    TestElasticsearchConfiguration.class,
    TestStorageConfiguration.class
})
class SavedArticleTests {

    private static final String PATH = "/api/v1/me/saved-articles";

    private final MockMvcTester mvc;
    private final TestUsers users;
    private final TestArticles articles;
    private final TestImages images;

    private TestUser user;

    @Autowired
    SavedArticleTests(MockMvcTester mvc, TestUsers users, TestArticles articles, TestImages images) {
        this.mvc = mvc;
        this.users = users;
        this.articles = articles;
        this.images = images;
    }

    @BeforeEach
    void startEmpty() {
        // Haberler silinince kayıtları da silinir (ON DELETE CASCADE).
        articles.clear();
        images.clearFiles();
        user = users.create(UserRole.USER, UserStatus.ACTIVE);
    }

    private MvcTestResult save(TestUser who, UUID articleId) {
        return mvc.put()
                .uri(PATH + "/" + articleId)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + who.token())
                .exchange();
    }

    private MvcTestResult remove(TestUser who, UUID articleId) {
        return mvc.delete()
                .uri(PATH + "/" + articleId)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + who.token())
                .exchange();
    }

    private MvcTestResult list(TestUser who, String query) {
        return mvc.get()
                .uri(PATH + "?" + query)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + who.token())
                .exchange();
    }

    @Test
    @DisplayName("kaydedilen haber listede sözleşmedeki alanlarla görünür: başlık, kaynak, yayın tarihi, görsel")
    void savedArticleAppearsInTheList() {
        UUID id = articles.insertRow(
                Article.turkish("Deprem sonrası son durum").publishedAt(Instant.parse("2026-11-05T08:12:00Z")));
        images.addDownloaded(id, 0, TestImages.png(30, 20), "image/png", 30, 20);

        assertThat(save(user, id)).hasStatus(HttpStatus.NO_CONTENT);
        MvcTestResult result = list(user, "");

        assertThat(result).hasStatusOk();
        assertThat(result)
                .bodyJson()
                .extractingPath("$")
                .asMap()
                .containsOnlyKeys("items", "page", "size", "totalElements", "totalPages")
                .containsEntry("page", 0)
                .containsEntry("size", 20)
                .containsEntry("totalElements", 1)
                .containsEntry("totalPages", 1);
        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[0]")
                .asMap()
                .containsOnlyKeys("articleId", "savedAt", "hidden", "article")
                .containsEntry("articleId", id.toString())
                .containsEntry("hidden", false);
        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[0].article")
                .asMap()
                .containsOnlyKeys("title", "source", "publishedAt", "image")
                .containsEntry("title", "Deprem sonrası son durum")
                .containsEntry("publishedAt", "2026-11-05T08:12:00Z")
                .containsEntry("source", Map.of("code", "TRT", "name", "TRT Haber"));
        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[0].article.image.url")
                .asString()
                .startsWith("/api/v1/media/");
    }

    @Test
    @DisplayName("aynı haberi ikinci kez kaydetmek bir şey değiştirmez; kaydedilme zamanı ilk kayıttaki kalır")
    void savingTwiceChangesNothing() {
        UUID id = articles.insertRow(Article.turkish("Haber"));
        save(user, id);
        String firstSavedAt = assertThat(list(user, ""))
                .bodyJson()
                .extractingPath("$.items[0].savedAt")
                .asString()
                .actual();

        assertThat(save(user, id)).hasStatus(HttpStatus.NO_CONTENT);

        MvcTestResult result = list(user, "");
        assertThat(result).bodyJson().extractingPath("$.totalElements").isEqualTo(1);
        assertThat(result).bodyJson().extractingPath("$.items[0].savedAt").isEqualTo(firstSavedAt);
    }

    @Test
    @DisplayName("kayıttan çıkarılan haber listeden gider; kayıtlı olmayanı çıkarmak da 204 döner")
    void removedArticleLeavesTheList() {
        UUID id = articles.insertRow(Article.turkish("Haber"));
        save(user, id);

        assertThat(remove(user, id)).hasStatus(HttpStatus.NO_CONTENT);

        assertThat(list(user, "")).bodyJson().extractingPath("$.totalElements").isEqualTo(0);
        assertThat(remove(user, id)).hasStatus(HttpStatus.NO_CONTENT);
    }

    @Test
    @DisplayName("liste kaydedilme zamanına göre yeniden eskiye sıralı ve sayfalıdır (FG-KO-02)")
    void newestSavedComesFirstAndPagesAreCounted() {
        UUID first = articles.insertRow(Article.turkish("Birinci"));
        UUID second = articles.insertRow(Article.turkish("İkinci"));
        UUID third = articles.insertRow(Article.turkish("Üçüncü"));
        save(user, first);
        save(user, second);
        save(user, third);

        MvcTestResult firstPage = list(user, "size=2");
        MvcTestResult secondPage = list(user, "size=2&page=1");

        assertThat(firstPage)
                .bodyJson()
                .extractingPath("$.items[*].articleId")
                .asArray()
                .containsExactly(third.toString(), second.toString());
        assertThat(firstPage).bodyJson().extractingPath("$.totalElements").isEqualTo(3);
        assertThat(firstPage).bodyJson().extractingPath("$.totalPages").isEqualTo(2);
        assertThat(secondPage)
                .bodyJson()
                .extractingPath("$.items[*].articleId")
                .asArray()
                .containsExactly(first.toString());
    }

    @Test
    @DisplayName("gizlenmiş veya kayıtlı olmayan haber kaydedilemez: 404 NOT_FOUND")
    void hiddenOrUnknownArticleCannotBeSaved() {
        UUID hidden = articles.insertRow(Article.turkish("Gizli haber"));
        articles.hideRowOnly(hidden);

        MvcTestResult result = save(user, hidden);

        assertThat(result).hasStatus(HttpStatus.NOT_FOUND);
        assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("NOT_FOUND");
        assertThat(save(user, UUID.randomUUID())).hasStatus(HttpStatus.NOT_FOUND);
        assertThat(list(user, "")).bodyJson().extractingPath("$.totalElements").isEqualTo(0);
    }

    @Test
    @DisplayName("kaydedildikten sonra gizlenen haber listede kalır, gizlendi olarak işaretlenir (FG-KO-03)")
    void articleHiddenAfterSavingIsMarkedHidden() {
        UUID id = articles.insertRow(Article.turkish("Sonradan gizlenen haber"));
        save(user, id);

        articles.hideRowOnly(id);

        MvcTestResult result = list(user, "");
        assertThat(result).bodyJson().extractingPath("$.totalElements").isEqualTo(1);
        assertThat(result).bodyJson().extractingPath("$.items[0].articleId").isEqualTo(id.toString());
        assertThat(result).bodyJson().extractingPath("$.items[0].hidden").isEqualTo(true);
        assertThat(result).bodyJson().extractingPath("$.items[0].article").isNull();
    }

    @Test
    @DisplayName("bir kullanıcı başkasının kayıtlarını göremez ve çıkaramaz")
    void usersSeeOnlyTheirOwnSavedArticles() {
        UUID id = articles.insertRow(Article.turkish("Haber"));
        TestUser other = users.create(UserRole.USER, UserStatus.ACTIVE);
        save(user, id);

        assertThat(list(other, "")).bodyJson().extractingPath("$.totalElements").isEqualTo(0);
        assertThat(remove(other, id)).hasStatus(HttpStatus.NO_CONTENT);

        assertThat(list(user, "")).bodyJson().extractingPath("$.totalElements").isEqualTo(1);
    }

    @Test
    @DisplayName("geçersiz page ve size değerleri birlikte bildirilir: 400 VALIDATION_FAILED")
    void invalidPageParametersAreRejected() {
        MvcTestResult result = list(user, "size=101&page=-1");

        assertThat(result).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("VALIDATION_FAILED");
        assertThat(result)
                .bodyJson()
                .extractingPath("$.errors[?(@.field == 'size')].code")
                .asArray()
                .containsExactly("MAX_VALUE");
        assertThat(result)
                .bodyJson()
                .extractingPath("$.errors[?(@.field == 'page')].code")
                .asArray()
                .containsExactly("MIN_VALUE");
    }

    @Test
    @DisplayName("haber kimliği geçerli bir UUID değilse 400 VALIDATION_FAILED döner")
    void malformedArticleIdIsRejected() {
        MvcTestResult result = mvc.put()
                .uri(PATH + "/haber-1")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + user.token())
                .exchange();

        assertThat(result).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("VALIDATION_FAILED");
    }

    @Test
    @DisplayName("kaydedilen haberler yalnızca aktif kullanıcıya açıktır")
    void savedArticlesRequireAnActiveUser() {
        UUID id = articles.insertRow(Article.turkish("Haber"));
        TestUser pending = users.create(UserRole.USER, UserStatus.PENDING);

        assertThat(mvc.get().uri(PATH)).hasStatus(HttpStatus.UNAUTHORIZED);
        assertThat(list(pending, "")).hasStatus(HttpStatus.FORBIDDEN);
        assertThat(save(pending, id)).hasStatus(HttpStatus.FORBIDDEN);
    }
}
