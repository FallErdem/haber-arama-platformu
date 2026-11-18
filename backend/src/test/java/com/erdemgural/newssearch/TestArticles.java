package com.erdemgural.newssearch;

import java.sql.Timestamp;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import tools.jackson.databind.json.JsonMapper;

/**
 * Testler için haber oluşturur: kümede Python işçisinin yaptığı gibi haberin meta verisini
 * PostgreSQL'e, belgesini (metinleriyle birlikte) Elasticsearch'e yazar. Özet, tam metin ve yazar
 * yalnızca belgededir (ADR-0019). Belgenin alanları işçinin ürettiği belgeyle aynıdır
 * (worker/src/news_worker/search_document.py); test indeksi tanımsız alanı reddettiği için buradaki bir
 * alan adı hatası sessiz kalmaz.
 */
public class TestArticles {

    private static final DateTimeFormatter MONTH =
            DateTimeFormatter.ofPattern("yyyy.MM").withZone(ZoneOffset.UTC);

    /**
     * Bir test haberi. Değiştirmek için {@code with...} metotları yeni bir kopya döner.
     *
     * @param content tam metnin yazısı; belgeye işçinin yaptığı gibi HTML paragrafı olarak yazılır
     */
    public record Article(
            String sourceCode,
            String language,
            String title,
            String summary,
            String content,
            String author,
            Instant publishedAt,
            List<String> categories) {

        public static Article turkish(String title) {
            return new Article(
                    "TRT", "tr", title, null, null, null, Instant.now().minusSeconds(3600), List.of("GENERAL"));
        }

        public static Article english(String title) {
            return new Article(
                    "GLOBALVOICES", "en", title, null, null, null, Instant.now().minusSeconds(3600), List.of("WORLD"));
        }

        public Article withSource(String code) {
            return new Article(code, language, title, summary, content, author, publishedAt, categories);
        }

        public Article withSummary(String text) {
            return new Article(sourceCode, language, title, text, content, author, publishedAt, categories);
        }

        public Article withContent(String text) {
            return new Article(sourceCode, language, title, summary, text, author, publishedAt, categories);
        }

        public Article withAuthor(String name) {
            return new Article(sourceCode, language, title, summary, content, name, publishedAt, categories);
        }

        public Article publishedAt(Instant instant) {
            return new Article(sourceCode, language, title, summary, content, author, instant, categories);
        }

        public Article withCategories(String... codes) {
            return new Article(sourceCode, language, title, summary, content, author, publishedAt, List.of(codes));
        }
    }

    private final JdbcClient jdbcClient;
    private final TestSearchIndex searchIndex;
    private final JsonMapper jsonMapper = JsonMapper.builder().build();

    TestArticles(JdbcClient jdbcClient, TestSearchIndex searchIndex) {
        this.jdbcClient = jdbcClient;
        this.searchIndex = searchIndex;
    }

    /** Haberi hem PostgreSQL'e hem arama indeksine yazar ve kimliğini döner. */
    public UUID add(Article article) {
        UUID id = insertRow(article);
        indexDocument(id, article, false);
        return id;
    }

    /** Haberin yalnızca meta verisini PostgreSQL'e yazar (arama indeksinde belgesi yoktur). */
    public UUID insertRow(Article article) {
        String key = UUID.randomUUID().toString();
        UUID id = jdbcClient
                .sql("""
				INSERT INTO articles (
				    source_id, external_id, url, normalized_url, title,
				    language, item_type, published_at, fetched_at, lifecycle_state)
				SELECT id, :key, :url, :url, :title,
				       :language, 'ARTICLE', :publishedAt, now(), 'HOT'
				FROM sources
				WHERE code = :sourceCode
				RETURNING id
				""")
                .param("key", key)
                .param("url", "https://example.test/haber/" + key)
                .param("title", article.title())
                .param("language", article.language())
                .param("publishedAt", Timestamp.from(article.publishedAt()))
                .param("sourceCode", article.sourceCode())
                .query(UUID.class)
                .single();
        for (String category : article.categories()) {
            jdbcClient.sql("""
					INSERT INTO article_categories (article_id, category_id, mapping_level)
					SELECT :articleId, id, 'FEED' FROM categories WHERE code = :code
					""").param("articleId", id).param("code", category).update();
        }
        return id;
    }

    /**
     * Haberin belgesini, işçinin yaptığı gibi yayın ayının indeksine yazar. Tam metin HTML paragrafı
     * olarak yazılır; etiketleri arama analizörü atar.
     */
    public void indexDocument(UUID id, Article article, boolean hidden) {
        Map<String, Object> document = new LinkedHashMap<>();
        document.put("source_code", article.sourceCode());
        document.put("language", article.language());
        document.put("item_type", "ARTICLE");
        document.put("categories", article.categories());
        document.put("published_at", article.publishedAt().toString());
        document.put("hidden", hidden);
        document.put("title_" + article.language(), article.title());
        if (article.summary() != null) {
            document.put("summary_" + article.language(), article.summary());
        }
        if (article.content() != null) {
            document.put("content_" + article.language(), "<p>" + article.content() + "</p>");
        }
        if (article.author() != null) {
            document.put("author", article.author());
        }
        String index = "articles-g1-" + MONTH.format(article.publishedAt()) + ".01";
        searchIndex.index(index, id.toString(), jsonMapper.writeValueAsString(document));
    }

    /**
     * Haberi işçi gizleme notunu işledikten sonraki haline getirir: PostgreSQL'de gizli, belgesi indekste
     * kalır ve gizli olarak işaretlenir (ADR-0019).
     */
    public void hide(UUID id, Article article) {
        hideRowOnly(id);
        indexDocument(id, article, true);
    }

    /** Haberi yalnızca PostgreSQL'de gizler; arama indeksindeki kopyası durur (outbox notu henüz işlenmemiş gibi). */
    public void hideRowOnly(UUID id) {
        UUID adminId = jdbcClient
                .sql("""
				INSERT INTO users (keycloak_sub, email, role, status)
				VALUES (:sub, :email, 'ADMIN', 'ACTIVE')
				RETURNING id
				""")
                .param("sub", UUID.randomUUID().toString())
                .param("email", UUID.randomUUID() + "@example.test")
                .query(UUID.class)
                .single();
        jdbcClient
                .sql("UPDATE articles SET hidden = true, hidden_at = now(), hidden_by = :adminId WHERE id = :id")
                .param("adminId", adminId)
                .param("id", id)
                .update();
    }

    /** Haberi yalnızca PostgreSQL'den siler; arama indeksindeki kopyası durur. */
    public void deleteRowOnly(UUID id) {
        jdbcClient.sql("DELETE FROM articles WHERE id = :id").param("id", id).update();
    }

    /** Bütün test haberlerini PostgreSQL'den ve arama indeksinden siler. */
    public void clear() {
        jdbcClient.sql("DELETE FROM articles").update();
        searchIndex.clear();
    }
}
