package com.erdemgural.newssearch.search;

import static org.assertj.core.api.Assertions.assertThat;

import com.erdemgural.newssearch.TestArticles;
import com.erdemgural.newssearch.TestArticles.Article;
import com.erdemgural.newssearch.TestDatabaseConfiguration;
import com.erdemgural.newssearch.TestElasticsearchConfiguration;
import com.erdemgural.newssearch.TestKeycloakConfiguration;
import com.erdemgural.newssearch.TestUsers;
import com.erdemgural.newssearch.TestUsers.TestUser;
import com.erdemgural.newssearch.identity.UserRole;
import com.erdemgural.newssearch.identity.UserStatus;
import java.time.Duration;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.IntStream;
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
 * {@code GET /api/v1/articles} (API sözleşmesi 4.1). Gerçek PostgreSQL ve gerçek Elasticsearch
 * ile; indeks yapısı işçinin kurduğuyla aynıdır.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import({TestDatabaseConfiguration.class, TestKeycloakConfiguration.class, TestElasticsearchConfiguration.class})
class ArticleSearchTests {

    private static final String PATH = "/api/v1/articles";

    private final MockMvcTester mvc;
    private final TestUsers users;
    private final TestArticles articles;

    private TestUser user;

    @Autowired
    ArticleSearchTests(MockMvcTester mvc, TestUsers users, TestArticles articles) {
        this.mvc = mvc;
        this.users = users;
        this.articles = articles;
    }

    @BeforeEach
    void startEmpty() {
        articles.clear();
        user = users.create(UserRole.USER, UserStatus.ACTIVE);
    }

    // --- Anahtar kelime (FG-AR-01, FG-AR-11) ----------------------------------------------------

    @Test
    @DisplayName("arama ifadesi başlıkta, özette ve içerikte aranır")
    void queryIsSearchedInTitleSummaryAndContent() {
        UUID inTitle = articles.add(Article.turkish("Deprem sonrası son durum"));
        UUID inSummary = articles.add(Article.turkish("Bölgeden haberler").withSummary("Deprem bölgesinde çalışmalar"));
        UUID inContent = articles.add(Article.turkish("Vali açıklama yaptı").withContent("Depremden etkilenenler"));
        articles.add(Article.turkish("Hava durumu raporu"));

        MvcTestResult result = search("q=deprem");

        assertThat(ids(result)).containsExactlyInAnyOrder(inTitle, inSummary, inContent);
    }

    @Test
    @DisplayName("başlıktaki eşleşme özettekinden, özetteki içeriktekinden önce gelir")
    void titleMatchRanksAboveSummaryAndContentMatch() {
        String filler = "Yetkililer bugün konuyla ilgili bilgi verdi";
        UUID inContent =
                articles.add(Article.turkish(filler).withSummary(filler).withContent("Seçim takvimi açıklandı"));
        UUID inTitle = articles.add(
                Article.turkish("Seçim takvimi açıklandı").withSummary(filler).withContent(filler));
        UUID inSummary = articles.add(
                Article.turkish(filler).withSummary("Seçim takvimi açıklandı").withContent(filler));

        MvcTestResult result = search("q=seçim");

        assertThat(ids(result)).containsExactly(inTitle, inSummary, inContent);
    }

    @Test
    @DisplayName("Türkçe haber, kelimenin başka ekli ve başka büyük/küçük harfli halleriyle bulunur")
    void turkishArticleIsFoundByInflectedForms() {
        UUID id = articles.add(Article.turkish("İstanbul'daki kitapları inceledi"));

        assertThat(ids(search("q=kitap"))).containsExactly(id);
        assertThat(ids(search("q=İSTANBUL"))).containsExactly(id);
        assertThat(ids(search("q=istanbul kitaplar"))).containsExactly(id);
    }

    @Test
    @DisplayName("Türkçe karaktersiz veya noktasız büyük I ile yazılan sorgu da haberi bulur")
    void queryWithoutTurkishLettersFindsTheArticle() {
        UUID id = articles.add(Article.turkish("Cumhurbaşkanı İstanbul'da açıklama yaptı"));

        assertThat(ids(search("q=cumhurbaskani"))).containsExactly(id);
        assertThat(ids(search("q=ISTANBUL"))).containsExactly(id);
        assertThat(ids(search("q=Istanbul aciklama"))).containsExactly(id);
    }

    @Test
    @DisplayName("asıl alanda eşleşen haber, yalnızca katlanmış alanda eşleşenden önce gelir")
    void exactMatchRanksAboveFoldedOnlyMatch() {
        // "cumhuriyet" yalnızca ilk beş harfiyle (cumhu) eşleşir; bu kaba bir eşleşmedir.
        UUID coarse = articles.add(Article.turkish("Cumhuriyet Bayramı kutlandı"));
        UUID exact = articles.add(Article.turkish("Cumhurbaşkanı törene katıldı"));

        MvcTestResult result = search("q=cumhurbaşkanı");

        assertThat(ids(result)).containsExactly(exact, coarse);
    }

    @Test
    @DisplayName("İngilizce haber İngilizce kök bulmayla aranır")
    void englishArticleIsFoundByStem() {
        UUID id = articles.add(Article.english("Volunteers are running a library"));

        assertThat(ids(search("q=run libraries"))).containsExactly(id);
    }

    @Test
    @DisplayName("iki kelimelik sorguda iki kelime de geçmelidir; kelimeler farklı alanlarda olabilir")
    void twoWordQueryRequiresBothWordsAcrossFields() {
        UUID both = articles.add(Article.turkish("Galatasaray kazandı").withContent("Rakibi Fenerbahçe oldu"));
        articles.add(Article.turkish("Galatasaray antrenman yaptı"));

        assertThat(ids(search("q=galatasaray fenerbahçe"))).containsExactly(both);
    }

    @Test
    @DisplayName("dört kelimelik sorguda üç kelimenin geçmesi yeterlidir, ikisi yetmez")
    void longQueryRequiresMostWords() {
        UUID three = articles.add(Article.turkish("Merkez Bankası faiz açıklaması"));
        articles.add(Article.turkish("Merkez Bankası rezervleri arttı"));

        assertThat(ids(search("q=merkez bankası faiz kararı"))).containsExactly(three);
    }

    // --- Filtreler (FG-AR-02) -------------------------------------------------------------------

    @Test
    @DisplayName("kaynak filtresi yalnızca seçilen kaynakların haberlerini getirir")
    void sourceFilterKeepsSelectedSources() {
        UUID trt = articles.add(Article.turkish("Deprem haberi bir"));
        UUID ntv = articles.add(Article.turkish("Deprem haberi iki").withSource("NTV"));
        articles.add(Article.turkish("Deprem haberi üç").withSource("CNNTURK"));

        assertThat(ids(search("q=deprem&sources=TRT,NTV"))).containsExactlyInAnyOrder(trt, ntv);
        assertThat(ids(search("sources=NTV"))).containsExactly(ntv);
    }

    @Test
    @DisplayName("dil filtresi yalnızca o dildeki haberleri getirir")
    void languageFilterKeepsThatLanguage() {
        UUID turkish = articles.add(Article.turkish("Türkçe bir haber"));
        UUID english = articles.add(Article.english("An English article"));

        assertThat(ids(search("language=tr"))).containsExactly(turkish);
        assertThat(ids(search("language=en"))).containsExactly(english);
    }

    @Test
    @DisplayName("kategori filtresi seçilen kategorilerden herhangi birini taşıyan haberleri getirir")
    void categoryFilterMatchesAnySelectedCategory() {
        UUID sports = articles.add(Article.turkish("Maç sonucu").withCategories("SPORTS"));
        UUID economy = articles.add(Article.turkish("Borsa günü").withCategories("ECONOMY", "GENERAL"));
        articles.add(Article.turkish("Sağlık haberi").withCategories("HEALTH"));

        assertThat(ids(search("categories=SPORTS,ECONOMY"))).containsExactlyInAnyOrder(sports, economy);
    }

    @Test
    @DisplayName("tarih aralığı filtresi sınırlar dahil çalışır")
    void dateRangeFilterIsInclusive() {
        Instant day = Instant.parse("2026-10-10T12:00:00Z");
        UUID before = articles.add(Article.turkish("Önceki haber").publishedAt(day.minus(2, ChronoUnit.DAYS)));
        UUID exact = articles.add(Article.turkish("Tam o an").publishedAt(day));
        UUID after = articles.add(Article.turkish("Sonraki haber").publishedAt(day.plus(2, ChronoUnit.DAYS)));

        assertThat(ids(search("from=2026-10-10T12:00:00Z"))).containsExactlyInAnyOrder(exact, after);
        assertThat(ids(search("to=2026-10-10T12:00:00Z"))).containsExactlyInAnyOrder(exact, before);
        assertThat(ids(search("from=2026-10-09T00:00:00Z&to=2026-10-11T00:00:00Z")))
                .containsExactly(exact);
    }

    // --- Son Dakika (FG-AR-12) ------------------------------------------------------------------

    @Test
    @DisplayName("Son Dakika filtresi yalnızca son altı saatte yayımlanan son dakika haberlerini getirir")
    void breakingFilterKeepsOnlyRecentBreakingNews() {
        Instant now = Instant.now();
        UUID fresh = articles.add(Article.turkish("Yeni son dakika")
                .withCategories("GENERAL", "BREAKING")
                .publishedAt(now.minus(Duration.ofHours(5))));
        UUID expired = articles.add(Article.turkish("Eski son dakika")
                .withCategories("GENERAL", "BREAKING")
                .publishedAt(now.minus(Duration.ofHours(7))));
        articles.add(
                Article.turkish("Sıradan haber").withCategories("GENERAL").publishedAt(now.minus(Duration.ofHours(1))));

        assertThat(ids(search("categories=BREAKING"))).containsExactly(fresh);
        // Süresi dolan haber konu kategorisinde görünmeye devam eder.
        assertThat(ids(search("categories=GENERAL"))).contains(fresh, expired);
    }

    @Test
    @DisplayName("süresi dolan haberin kategorileri arasında Son Dakika gösterilmez")
    void expiredBreakingCategoryIsNotShown() {
        Instant now = Instant.now();
        articles.add(Article.turkish("Yeni son dakika")
                .withCategories("GENERAL", "BREAKING")
                .publishedAt(now.minus(Duration.ofHours(1))));
        articles.add(Article.turkish("Eski son dakika")
                .withCategories("GENERAL", "BREAKING")
                .publishedAt(now.minus(Duration.ofHours(7))));

        MvcTestResult result = search("sort=newest");

        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[0].categories")
                .asArray()
                .containsExactly("GENERAL", "BREAKING");
        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[1].categories")
                .asArray()
                .containsExactly("GENERAL");
    }

    // --- Sıralama (FG-AR-04) ve soğuk haberler (ADR-0011) -----------------------------------------

    @Test
    @DisplayName("arama ifadesi yokken haberler en yeniden eskiye listelenir; relevance yok sayılır")
    void withoutQueryArticlesAreListedNewestFirst() {
        Instant now = Instant.now();
        UUID oldest = articles.add(Article.turkish("Üçüncü").publishedAt(now.minus(Duration.ofDays(3))));
        UUID newest = articles.add(Article.turkish("Birinci").publishedAt(now.minus(Duration.ofHours(1))));
        UUID middle = articles.add(Article.turkish("İkinci").publishedAt(now.minus(Duration.ofDays(1))));

        assertThat(ids(search(""))).containsExactly(newest, middle, oldest);
        assertThat(ids(search("sort=relevance"))).containsExactly(newest, middle, oldest);
    }

    @Test
    @DisplayName("sort=newest ilgililiği değil yayın tarihini esas alır")
    void newestSortIgnoresRelevance() {
        Instant now = Instant.now();
        UUID strongButOld =
                articles.add(Article.turkish("Deprem deprem deprem").publishedAt(now.minus(Duration.ofDays(5))));
        UUID weakButNew = articles.add(Article.turkish("Vali konuştu")
                .withContent("Deprem bölgesi ziyaret edildi")
                .publishedAt(now.minus(Duration.ofHours(1))));

        assertThat(ids(search("q=deprem"))).containsExactly(strongButOld, weakButNew);
        assertThat(ids(search("q=deprem&sort=newest"))).containsExactly(weakButNew, strongButOld);
    }

    @Test
    @DisplayName("bir yıldan eski haber ilgililik sıralamasında geriye düşer ama sonuçta kalır")
    void coldArticleIsDemotedButStillFound() {
        Instant now = Instant.now();
        String filler = "Yetkililer bugün konuyla ilgili bilgi verdi";
        // Başlıktaki eşleşme normalde özettekinden önce gelir; aşağıdaki kontrol haberi bunu gösterir.
        UUID warmTitle = articles.add(Article.turkish("Bütçe görüşmeleri başladı")
                .withSummary(filler)
                .publishedAt(now.minus(Duration.ofDays(200))));
        UUID freshSummary = articles.add(Article.turkish(filler)
                .withSummary("Bütçe görüşmeleri başladı")
                .publishedAt(now.minus(Duration.ofDays(2))));
        assertThat(ids(search("q=bütçe"))).containsExactly(warmTitle, freshSummary);

        articles.clear();
        UUID coldTitle = articles.add(Article.turkish("Bütçe görüşmeleri başladı")
                .withSummary(filler)
                .publishedAt(now.minus(Duration.ofDays(400))));
        freshSummary = articles.add(Article.turkish(filler)
                .withSummary("Bütçe görüşmeleri başladı")
                .publishedAt(now.minus(Duration.ofDays(2))));

        assertThat(ids(search("q=bütçe"))).containsExactly(freshSummary, coldTitle);
    }

    // --- Vurgulama (FG-AR-05) -------------------------------------------------------------------

    @Test
    @DisplayName("eşleşen kelimeler başlıkta ve özette <mark> ile işaretlenir")
    void matchedWordsAreMarkedInTitleAndSummary() {
        articles.add(
                Article.turkish("Deprem sonrası son durum").withSummary("Bölgede deprem sonrası çalışmalar sürüyor"));

        MvcTestResult result = search("q=deprem");

        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[0].highlights.title")
                .asArray()
                .containsExactly("<mark>Deprem</mark> sonrası son durum");
        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[0].highlights.summary")
                .asArray()
                .containsExactly("Bölgede <mark>deprem</mark> sonrası çalışmalar sürüyor");
    }

    @Test
    @DisplayName("vurgulanan metindeki etiketler kaçış koduna çevrilir; yanıtta yalnızca <mark> gerçek etikettir")
    void highlightedTextIsHtmlEscaped() {
        articles.add(Article.turkish("Deprem <script>alert(1)</script> & sonrası"));

        MvcTestResult result = search("q=deprem");

        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[0].highlights.title[0]")
                .asString()
                .startsWith("<mark>Deprem</mark> ")
                .contains("&lt;script&gt;")
                .contains("&amp;")
                .doesNotContain("<script>");
    }

    @Test
    @DisplayName("eşleşme yalnızca katlanmış alandaysa kelime yine işaretlenir")
    void foldedOnlyMatchIsStillMarked() {
        articles.add(Article.turkish("İstanbul'da yağış bekleniyor"));

        MvcTestResult result = search("q=ISTANBUL");

        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[0].highlights.title[0]")
                .asString()
                .startsWith("<mark>İstanbul")
                .endsWith("yağış bekleniyor");
    }

    @Test
    @DisplayName("arama ifadesi yokken yanıtta highlights alanı bulunmaz")
    void highlightsAreAbsentWithoutQuery() {
        articles.add(Article.turkish("Herhangi bir haber"));

        MvcTestResult result = search("");

        assertThat(result).bodyJson().extractingPath("$.items[0]").asMap().doesNotContainKey("highlights");
    }

    // --- Yanıtın biçimi ---------------------------------------------------------------------------

    @Test
    @DisplayName("sonuçtaki haber sözleşmedeki alanları taşır; bilgiler asıl kayıttan gelir")
    void itemCarriesContractFields() {
        Instant publishedAt = Instant.parse("2026-11-05T08:12:00Z");
        UUID id = articles.add(Article.turkish("Deprem sonrası son durum")
                .withSummary("Bölgede çalışmalar sürüyor")
                .withCategories("GENERAL", "WORLD")
                .publishedAt(publishedAt));

        MvcTestResult result = search("q=deprem");

        assertThat(result).hasStatusOk();
        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[0]")
                .asMap()
                .containsOnlyKeys(
                        "id",
                        "title",
                        "highlights",
                        "summary",
                        "source",
                        "language",
                        "itemType",
                        "categories",
                        "publishedAt",
                        "url",
                        "image",
                        "otherSourcesCount")
                .containsEntry("id", id.toString())
                .containsEntry("title", "Deprem sonrası son durum")
                .containsEntry("summary", "Bölgede çalışmalar sürüyor")
                .containsEntry("language", "tr")
                .containsEntry("itemType", "ARTICLE")
                .containsEntry("publishedAt", "2026-11-05T08:12:00Z")
                // Görsel uç noktası (İ-18) ve kaynaklar arası gruplama (İ-28) henüz yok.
                .containsEntry("image", null)
                .containsEntry("otherSourcesCount", 0);
        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[0].source")
                .asMap()
                .containsOnly(Map.entry("code", "TRT"), Map.entry("name", "TRT Haber"));
        // Kategoriler arayüzdeki sırayla (sort_order) döner.
        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[0].categories")
                .asArray()
                .containsExactly("GENERAL", "WORLD");
        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[0].url")
                .asString()
                .startsWith("https://example.test/haber/");
    }

    // --- Sayfalama (FG-AR-03) ---------------------------------------------------------------------

    @Test
    @DisplayName("sonuçlar sayfalanır; toplam sayı ve sayfa sayısı yanıtta döner")
    void resultsArePaged() {
        Instant now = Instant.now();
        List<UUID> newestFirst = IntStream.range(0, 5)
                .mapToObj(hour -> articles.add(
                        Article.turkish("Haber " + hour).publishedAt(now.minus(Duration.ofHours(hour + 1)))))
                .toList();

        MvcTestResult firstPage = search("size=2");
        MvcTestResult lastPage = search("size=2&page=2");

        assertThat(ids(firstPage)).containsExactly(newestFirst.get(0), newestFirst.get(1));
        assertThat(ids(lastPage)).containsExactly(newestFirst.get(4));
        assertThat(firstPage).bodyJson().extractingPath("$.page").isEqualTo(0);
        assertThat(firstPage).bodyJson().extractingPath("$.size").isEqualTo(2);
        assertThat(firstPage).bodyJson().extractingPath("$.totalElements").isEqualTo(5);
        assertThat(firstPage).bodyJson().extractingPath("$.totalPages").isEqualTo(3);
        assertThat(firstPage).bodyJson().extractingPath("$.totalRelation").isEqualTo("eq");
        assertThat(lastPage).bodyJson().extractingPath("$.page").isEqualTo(2);
    }

    @Test
    @DisplayName("varsayılan sayfa boyutu 20'dir")
    void defaultPageSizeIsTwenty() {
        assertThat(search("")).bodyJson().extractingPath("$.size").isEqualTo(20);
    }

    @Test
    @DisplayName("10.000. sonucun ötesine sayfalama 400 PAGE_LIMIT_EXCEEDED ile reddedilir")
    void pagingBeyondTheLimitIsRejected() {
        // (99 + 1) x 100 = 10.000: sınırın kendisi kabul edilir.
        assertThat(search("page=99&size=100")).hasStatusOk();

        MvcTestResult result = search("page=100&size=100");

        assertThat(result).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("PAGE_LIMIT_EXCEEDED");
    }

    // --- Girdi doğrulama --------------------------------------------------------------------------

    @Test
    @DisplayName("geçersiz parametreler 400 VALIDATION_FAILED ile, alan adı ve koduyla birlikte bildirilir")
    void invalidParametersAreReportedPerField() {
        MvcTestResult result = search("size=101&page=-1&language=de&sort=oldest&from=dün");

        assertThat(result).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(result).hasContentType("application/problem+json");
        assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("VALIDATION_FAILED");
        assertThat(result)
                .bodyJson()
                .extractingPath("$.errors[*].field")
                .asArray()
                .containsExactlyInAnyOrder("size", "page", "language", "sort", "from");
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
    @DisplayName("200 karakterden uzun arama ifadesi ve ters tarih aralığı reddedilir")
    void tooLongQueryAndReversedRangeAreRejected() {
        MvcTestResult tooLong = search("q=" + "a".repeat(201));
        MvcTestResult reversed = search("from=2026-11-10T00:00:00Z&to=2026-11-01T00:00:00Z");

        assertThat(tooLong).bodyJson().extractingPath("$.errors[0].code").isEqualTo("MAX_LENGTH");
        assertThat(reversed).bodyJson().extractingPath("$.errors[0].field").isEqualTo("from");
        assertThat(reversed).bodyJson().extractingPath("$.errors[0].code").isEqualTo("INVALID_RANGE");
        assertThat(search("q=" + "a".repeat(200))).hasStatusOk();
    }

    // --- İndeks ile asıl kaydın ayrıştığı durumlar (FG-AR-09) --------------------------------------

    @Test
    @DisplayName("gizlenen haber, arama indeksindeki kopyası henüz silinmemiş olsa da sonuçta görünmez")
    void hiddenArticleIsNotShownEvenIfStillIndexed() {
        UUID visible = articles.add(Article.turkish("Deprem haberi bir"));
        UUID hidden = articles.add(Article.turkish("Deprem haberi iki"));
        articles.hideRowOnly(hidden);

        assertThat(ids(search("q=deprem"))).containsExactly(visible);
    }

    @Test
    @DisplayName("asıl kaydı silinmiş haber, arama indeksinde kalmış olsa da sonuçta görünmez")
    void deletedArticleIsNotShownEvenIfStillIndexed() {
        UUID kept = articles.add(Article.turkish("Deprem haberi bir"));
        UUID deleted = articles.add(Article.turkish("Deprem haberi iki"));
        articles.deleteRowOnly(deleted);

        assertThat(ids(search("q=deprem"))).containsExactly(kept);
    }

    @Test
    @DisplayName("arama indeksi henüz hiç oluşmamışken arama boş sonuç döner, hata vermez")
    void searchOnAMissingIndexReturnsNothing() {
        MvcTestResult result = search("q=deprem");

        assertThat(result).hasStatusOk();
        assertThat(result).bodyJson().extractingPath("$.items").asArray().isEmpty();
        assertThat(result).bodyJson().extractingPath("$.totalElements").isEqualTo(0);
        assertThat(result).bodyJson().extractingPath("$.totalPages").isEqualTo(0);
    }

    // --- Erişim -----------------------------------------------------------------------------------

    @Test
    @DisplayName("token olmadan veya onay bekleyen kullanıcıyla arama yapılamaz")
    void searchRequiresAnActiveUser() {
        TestUser pending = users.create(UserRole.USER, UserStatus.PENDING);

        assertThat(mvc.get().uri(PATH)).hasStatus(HttpStatus.UNAUTHORIZED);
        assertThat(mvc.get()
                        .uri(PATH)
                        .header(HttpHeaders.AUTHORIZATION, "Bearer " + pending.token())
                        .exchange())
                .hasStatus(HttpStatus.FORBIDDEN);
    }

    private MvcTestResult search(String queryString) {
        // Sorgu metni olduğu gibi verilir; Türkçe karakterleri ve boşlukları MockMvc kodlar.
        var request = mvc.get().uri(PATH).header(HttpHeaders.AUTHORIZATION, "Bearer " + user.token());
        for (String pair : queryString.split("&")) {
            if (!pair.isEmpty()) {
                String[] parts = pair.split("=", 2);
                request = request.param(parts[0], parts.length > 1 ? parts[1] : "");
            }
        }
        return request.exchange();
    }

    private List<UUID> ids(MvcTestResult result) {
        assertThat(result).hasStatusOk();
        Object[] ids = assertThat(result)
                .bodyJson()
                .extractingPath("$.items[*].id")
                .asArray()
                .actual();
        return Arrays.stream(ids).map(id -> UUID.fromString(id.toString())).toList();
    }
}
