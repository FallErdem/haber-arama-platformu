package com.erdemgural.newssearch.ingestion.internal;

import com.erdemgural.newssearch.ingestion.ArticleCatalog;
import com.erdemgural.newssearch.ingestion.ArticleSummary;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class ArticleRepository implements ArticleCatalog {

    private final JdbcClient jdbcClient;

    ArticleRepository(JdbcClient jdbcClient) {
        this.jdbcClient = jdbcClient;
    }

    /**
     * Bir sayfadaki bütün haberler tek sorguyla okunur (haber başına ayrı sorgu atılmaz).
     * array_agg haberin kategori kodlarını tek bir dizide toplar; FILTER, kategorisi olmayan
     * haberde dizinin [NULL] yerine boş olmasını sağlar.
     */
    @Override
    public Map<UUID, ArticleSummary> findSummaries(Collection<UUID> articleIds) {
        if (articleIds.isEmpty()) {
            return Map.of();
        }
        return jdbcClient.sql("""
				SELECT a.id, a.title, a.summary, a.language, a.item_type, a.published_at, a.url,
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
				""").param("articleIds", articleIds).query(ArticleRepository::mapRow).list().stream()
                .collect(Collectors.toMap(ArticleSummary::id, Function.identity()));
    }

    private static ArticleSummary mapRow(ResultSet row, int rowNumber) throws SQLException {
        return new ArticleSummary(
                row.getObject("id", UUID.class),
                row.getString("title"),
                row.getString("summary"),
                row.getString("source_code"),
                row.getString("source_name"),
                row.getString("language"),
                row.getString("item_type"),
                List.of((String[]) row.getArray("categories").getArray()),
                row.getTimestamp("published_at").toInstant(),
                row.getString("url"));
    }
}
