package com.erdemgural.newssearch.ingestion.internal;

import com.erdemgural.newssearch.ingestion.ArticleSummary;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class ArticleRepository {

    /**
     * Haber detayı için PostgreSQL'den okunan meta veri: haber, kaynağı ve kategori kodları. Özet, tam
     * metin ve yazar burada yoktur; tek kayıtları Elasticsearch'tir (ADR-0019).
     */
    record ArticleDetailRow(
            UUID id,
            String title,
            String url,
            String sourceCode,
            String sourceName,
            String sourceHomepageUrl,
            String sourceAttributionText,
            String language,
            String itemType,
            List<String> categories,
            Instant publishedAt) {}

    private final JdbcClient jdbcClient;

    ArticleRepository(JdbcClient jdbcClient) {
        this.jdbcClient = jdbcClient;
    }

    /**
     * Bir sayfadaki bütün haberler tek sorguyla okunur (haber başına ayrı sorgu atılmaz).
     * array_agg haberin kategori kodlarını tek bir dizide toplar; FILTER, kategorisi olmayan
     * haberde dizinin [NULL] yerine boş olmasını sağlar. Ana görsel burada okunmaz
     * ({@link ArticleCatalogService}).
     */
    Map<UUID, ArticleSummary> findSummaries(Collection<UUID> articleIds) {
        if (articleIds.isEmpty()) {
            return Map.of();
        }
        return jdbcClient.sql("""
				SELECT a.id, a.title, a.language, a.item_type, a.published_at, a.url,
				       s.code AS source_code, s.name AS source_name,
				       COALESCE(
				           array_agg(c.code ORDER BY c.sort_order) FILTER (WHERE c.code IS NOT NULL),
				           '{}'::text[]) AS categories
				FROM articles a
				JOIN sources s ON s.id = a.source_id
				LEFT JOIN article_categories ac ON ac.article_id = a.id
				LEFT JOIN categories c ON c.id = ac.category_id
				WHERE a.id IN (:articleIds)
				  AND NOT a.hidden
				GROUP BY a.id, s.code, s.name
				""").param("articleIds", articleIds).query(ArticleRepository::mapSummary).list().stream()
                .collect(Collectors.toMap(ArticleSummary::id, Function.identity()));
    }

    /** Haber detayı; haber yoksa veya gizlenmişse boş döner (FG-AR-09). */
    Optional<ArticleDetailRow> findDetail(UUID articleId) {
        return jdbcClient
                .sql("""
				SELECT a.id, a.title, a.url, a.language, a.item_type, a.published_at,
				       s.code AS source_code, s.name AS source_name, s.homepage_url, s.attribution_text,
				       COALESCE(
				           array_agg(c.code ORDER BY c.sort_order) FILTER (WHERE c.code IS NOT NULL),
				           '{}'::text[]) AS categories
				FROM articles a
				JOIN sources s ON s.id = a.source_id
				LEFT JOIN article_categories ac ON ac.article_id = a.id
				LEFT JOIN categories c ON c.id = ac.category_id
				WHERE a.id = :articleId
				  AND NOT a.hidden
				GROUP BY a.id, s.code, s.name, s.homepage_url, s.attribution_text
				""")
                .param("articleId", articleId)
                .query(ArticleRepository::mapDetail)
                .optional();
    }

    private static ArticleSummary mapSummary(ResultSet row, int rowNumber) throws SQLException {
        return new ArticleSummary(
                row.getObject("id", UUID.class),
                row.getString("title"),
                row.getString("source_code"),
                row.getString("source_name"),
                row.getString("language"),
                row.getString("item_type"),
                categories(row),
                row.getTimestamp("published_at").toInstant(),
                row.getString("url"),
                null);
    }

    private static ArticleDetailRow mapDetail(ResultSet row, int rowNumber) throws SQLException {
        return new ArticleDetailRow(
                row.getObject("id", UUID.class),
                row.getString("title"),
                row.getString("url"),
                row.getString("source_code"),
                row.getString("source_name"),
                row.getString("homepage_url"),
                row.getString("attribution_text"),
                row.getString("language"),
                row.getString("item_type"),
                categories(row),
                row.getTimestamp("published_at").toInstant());
    }

    private static List<String> categories(ResultSet row) throws SQLException {
        return List.of((String[]) row.getArray("categories").getArray());
    }
}
