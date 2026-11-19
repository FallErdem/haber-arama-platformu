package com.erdemgural.newssearch.search;

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
import java.time.Duration;
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
 * {@code GET /api/v1/articles/{id}} (API sözleşmesi 4.2). Gerçek PostgreSQL, Elasticsearch ve MinIO ile:
 * meta veri ve görseller PostgreSQL'den, özet, tam metin ve yazar Elasticsearch'ten gelir (ADR-0019).
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import({
    TestDatabaseConfiguration.class,
    TestKeycloakConfiguration.class,
    TestElasticsearchConfiguration.class,
    TestStorageConfiguration.class
})
class ArticleDetailTests {

    private final MockMvcTester mvc;
    private final TestUsers users;
    private final TestArticles articles;
    private final TestImages images;

    private TestUser user;

    @Autowired
    ArticleDetailTests(MockMvcTester mvc, TestUsers users, TestArticles articles, TestImages images) {
        this.mvc = mvc;
        this.users = users;
        this.articles = articles;
        this.images = images;
    }

    @BeforeEach
    void startEmpty() {
        articles.clear();
        images.clearFiles();
        user = users.create(UserRole.USER, UserStatus.ACTIVE);
    }

    private MvcTestResult detail(UUID id) {
        return mvc.get()
                .uri("/api/v1/articles/" + id)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + user.token())
                .exchange();
    }

    @Test
    @DisplayName("detay sözleşmedeki bütün alanları taşır: tam metin, yazar, özgün adres, kaynak ve atıf")
    void detailCarriesAllContractFields() {
        Instant publishedAt = Instant.parse("2026-11-05T08:12:00Z");
        UUID id = articles.add(Article.turkish("Deprem sonrası son durum")
                .withSummary("Bölgede çalışmalar sürüyor")
                .withContent("Ekipler sahada.")
                .withAuthor("Örnek Yazar")
                .withCategories("GENERAL", "WORLD")
                .publishedAt(publishedAt));

        MvcTestResult result = detail(id);

        assertThat(result).hasStatusOk();
        assertThat(result)
                .bodyJson()
                .extractingPath("$")
                .asMap()
                .containsOnlyKeys(
                        "id",
                        "title",
                        "summary",
                        "content",
                        "author",
                        "url",
                        "source",
                        "language",
                        "itemType",
                        "categories",
                        "publishedAt",
                        "media",
                        "otherSources",
                        "saved")
                .containsEntry("id", id.toString())
                .containsEntry("title", "Deprem sonrası son durum")
                .containsEntry("summary", "Bölgede çalışmalar sürüyor")
                // İşçinin temizlediği HTML olduğu gibi döner (FOG-16).
                .containsEntry("content", "<p>Ekipler sahada.</p>")
                .containsEntry("author", "Örnek Yazar")
                .containsEntry("language", "tr")
                .containsEntry("itemType", "ARTICLE")
                .containsEntry("publishedAt", "2026-11-05T08:12:00Z")
                .containsEntry("saved", false);
        // Kaynaklar arası gruplama (İ-28) henüz yok.
        assertThat(result).bodyJson().extractingPath("$.otherSources").asArray().isEmpty();
        assertThat(result).bodyJson().extractingPath("$.categories").asArray().containsExactly("GENERAL", "WORLD");
        assertThat(result).bodyJson().extractingPath("$.url").asString().startsWith("https://example.test/haber/");
        // Kaynağın adı, ana sayfası ve atıf metni (FG-AR-07); başlangıç verisi V11.
        assertThat(result)
                .bodyJson()
                .extractingPath("$.source")
                .asMap()
                .containsOnly(
                        Map.entry("code", "TRT"),
                        Map.entry("name", "TRT Haber"),
                        Map.entry("homepageUrl", "https://www.trthaber.com"),
                        Map.entry("attributionText", "TRT Haber"));
    }

    @Test
    @DisplayName("saved alanı isteği yapan kullanıcıya göredir: kaydeden true, başka kullanıcı false görür")
    void savedFlagBelongsToTheRequestingUser() {
        UUID id = articles.insertRow(Article.turkish("Kaydedilecek haber"));
        TestUser other = users.create(UserRole.USER, UserStatus.ACTIVE);
        assertThat(mvc.put()
                        .uri("/api/v1/me/saved-articles/" + id)
                        .header(HttpHeaders.AUTHORIZATION, "Bearer " + user.token())
                        .exchange())
                .hasStatus(HttpStatus.NO_CONTENT);

        assertThat(detail(id)).bodyJson().extractingPath("$.saved").isEqualTo(true);
        assertThat(mvc.get()
                        .uri("/api/v1/articles/" + id)
                        .header(HttpHeaders.AUTHORIZATION, "Bearer " + other.token())
                        .exchange())
                .bodyJson()
                .extractingPath("$.saved")
                .isEqualTo(false);
    }

    @Test
    @DisplayName("tam metni olmayan haberde content null döner; arayüz özeti gösterir")
    void articleWithoutContentHasNullContent() {
        UUID id = articles.add(Article.turkish("Kısa haber").withSummary("Yalnızca özet var"));

        MvcTestResult result = detail(id);

        assertThat(result).bodyJson().extractingPath("$.content").isNull();
        assertThat(result).bodyJson().extractingPath("$.author").isNull();
        assertThat(result).bodyJson().extractingPath("$.summary").isEqualTo("Yalnızca özet var");
    }

    @Test
    @DisplayName("İngilizce haberin metinleri _en alanlarından okunur")
    void englishArticleTextsComeFromEnglishFields() {
        UUID id = articles.add(Article.english("Election results")
                .withSummary("Counting continues")
                .withContent("Polls closed at eight."));

        MvcTestResult result = detail(id);

        assertThat(result).bodyJson().extractingPath("$.summary").isEqualTo("Counting continues");
        assertThat(result).bodyJson().extractingPath("$.content").isEqualTo("<p>Polls closed at eight.</p>");
    }

    @Test
    @DisplayName("belgesi henüz aktarılmamış haber metinsiz döner; meta verisi ve görselleri gösterilir")
    void articleNotYetIndexedHasNoTexts() {
        UUID id = articles.insertRow(Article.turkish("Yeni kaydedilen haber"));
        images.addDownloaded(id, 0, TestImages.png(30, 20), "image/png", 30, 20);

        MvcTestResult result = detail(id);

        assertThat(result).hasStatusOk();
        assertThat(result).bodyJson().extractingPath("$.title").isEqualTo("Yeni kaydedilen haber");
        assertThat(result).bodyJson().extractingPath("$.summary").isNull();
        assertThat(result).bodyJson().extractingPath("$.content").isNull();
        assertThat(result).bodyJson().extractingPath("$.author").isNull();
        assertThat(result).bodyJson().extractingPath("$.media.length()").isEqualTo(1);
    }

    @Test
    @DisplayName("yalnızca indirilmiş görseller, haberdeki sırasıyla ve imzalı adresleriyle listelenir")
    void onlyDownloadedImagesAreListedInOrder() {
        UUID id = articles.insertRow(Article.turkish("Görselli haber"));
        UUID second = images.addDownloaded(id, 2, TestImages.png(20, 10), "image/png", 20, 10);
        images.addNotDownloaded(id, 1, "FAILED");
        UUID first = images.addDownloaded(id, 0, TestImages.png(30, 20), "image/png", 30, 20);
        images.addNotDownloaded(id, 3, "PENDING");

        MvcTestResult result = detail(id);

        assertThat(result).bodyJson().extractingPath("$.media.length()").isEqualTo(2);
        assertThat(result)
                .bodyJson()
                .extractingPath("$.media[0].url")
                .asString()
                .startsWith("/api/v1/media/" + first + "?exp=");
        assertThat(result)
                .bodyJson()
                .extractingPath("$.media[1].url")
                .asString()
                .startsWith("/api/v1/media/" + second + "?exp=");
        assertThat(result).bodyJson().extractingPath("$.media[0].width").isEqualTo(30);
        assertThat(result).bodyJson().extractingPath("$.media[0].height").isEqualTo(20);
        assertThat(result).bodyJson().extractingPath("$.media[0]").asMap().containsKeys("caption", "credit");
    }

    @Test
    @DisplayName("detaydaki görsel adresi gerçekten çalışır: token olmadan görseli döndürür")
    void imageUrlInDetailWorks() {
        UUID id = articles.insertRow(Article.turkish("Görselli haber"));
        byte[] body = TestImages.png(30, 20);
        images.addDownloaded(id, 0, body, "image/png", 30, 20);
        String url = assertThat(detail(id))
                .bodyJson()
                .extractingPath("$.media[0].url")
                .asString()
                .actual();

        MvcTestResult image = mvc.get().uri(url).exchange();

        assertThat(image).hasStatusOk();
        assertThat(image.getResponse().getContentAsByteArray()).isEqualTo(body);
    }

    @Test
    @DisplayName("görseli olmayan haberde media boş liste döner; arayüz yer tutucu gösterir (FG-AR-08)")
    void articleWithoutImagesHasEmptyMedia() {
        UUID id = articles.insertRow(Article.turkish("Görselsiz haber"));
        images.addNotDownloaded(id, 0, "FAILED");

        assertThat(detail(id)).bodyJson().extractingPath("$.media").asArray().isEmpty();
    }

    @Test
    @DisplayName("süresi dolan haberin kategorileri arasında Son Dakika gösterilmez (FG-AR-12)")
    void expiredBreakingCategoryIsNotShown() {
        UUID fresh = articles.insertRow(Article.turkish("Yeni")
                .withCategories("GENERAL", "BREAKING")
                .publishedAt(Instant.now().minus(Duration.ofHours(1))));
        UUID expired = articles.insertRow(Article.turkish("Eski")
                .withCategories("GENERAL", "BREAKING")
                .publishedAt(Instant.now().minus(Duration.ofHours(7))));

        assertThat(detail(fresh))
                .bodyJson()
                .extractingPath("$.categories")
                .asArray()
                .containsExactly("GENERAL", "BREAKING");
        assertThat(detail(expired))
                .bodyJson()
                .extractingPath("$.categories")
                .asArray()
                .containsExactly("GENERAL");
    }

    @Test
    @DisplayName("gizlenen veya kayıtlı olmayan haber 404 NOT_FOUND döner (FG-AR-09)")
    void hiddenOrUnknownArticleIsNotFound() {
        Article article = Article.turkish("Gizlenecek haber").withContent("Metni indekste kalır.");
        UUID hidden = articles.add(article);
        articles.hide(hidden, article);

        MvcTestResult hiddenResult = detail(hidden);

        assertThat(hiddenResult).hasStatus(HttpStatus.NOT_FOUND);
        assertThat(hiddenResult).bodyJson().extractingPath("$.code").isEqualTo("NOT_FOUND");
        assertThat(detail(UUID.randomUUID())).hasStatus(HttpStatus.NOT_FOUND);
    }

    @Test
    @DisplayName("gizleme notu henüz işlenmemişse de haber 404 döner: karar PostgreSQL'deki duruma göre verilir")
    void articleHiddenOnlyInDatabaseIsNotFound() {
        UUID id = articles.add(Article.turkish("Gizlenen haber").withContent("Belgesi henüz gizli değil."));
        articles.hideRowOnly(id);

        assertThat(detail(id)).hasStatus(HttpStatus.NOT_FOUND);
    }

    @Test
    @DisplayName("kimlik geçerli bir UUID değilse 400 VALIDATION_FAILED döner")
    void malformedIdIsRejected() {
        MvcTestResult result = mvc.get()
                .uri("/api/v1/articles/haber-1")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + user.token())
                .exchange();

        assertThat(result).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("VALIDATION_FAILED");
    }

    @Test
    @DisplayName("detay yalnızca aktif kullanıcıya açıktır")
    void detailRequiresAnActiveUser() {
        UUID id = articles.insertRow(Article.turkish("Haber"));
        TestUser pending = users.create(UserRole.USER, UserStatus.PENDING);

        assertThat(mvc.get().uri("/api/v1/articles/" + id)).hasStatus(HttpStatus.UNAUTHORIZED);
        assertThat(mvc.get()
                        .uri("/api/v1/articles/" + id)
                        .header(HttpHeaders.AUTHORIZATION, "Bearer " + pending.token())
                        .exchange())
                .hasStatus(HttpStatus.FORBIDDEN);
    }
}
