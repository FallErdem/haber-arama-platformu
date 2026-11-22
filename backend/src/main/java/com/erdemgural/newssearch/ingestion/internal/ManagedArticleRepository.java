package com.erdemgural.newssearch.ingestion.internal;

import static com.erdemgural.newssearch.ingestion.internal.ManagedSourceRepository.instant;

import com.erdemgural.newssearch.ingestion.ArticleFilter;
import com.erdemgural.newssearch.ingestion.ManagedArticle;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Yönetim panelinin {@code articles} sorguları: liste ve gizleme (FG-YP-09). */
@Repository
class ManagedArticleRepository {

    private static final String SELECT = """
			SELECT a.id, a.title, a.url, a.published_at, a.hidden, a.hidden_at, a.hidden_reason, a.hidden_by,
			       s.code AS source_code, s.name AS source_name
			FROM articles a
			JOIN sources s ON s.id = a.source_id
			""";

    private final JdbcClient jdbcClient;

    ManagedArticleRepository(JdbcClient jdbcClient) {
        this.jdbcClient = jdbcClient;
    }

    /** Filtreye uyan haberlerden bir sayfa. Gizli haberler en son gizlenen önce, diğerleri en yeni önce. */
    List<ManagedArticle> findPage(ArticleFilter filter, int limit, long offset) {
        String order = Boolean.TRUE.equals(filter.hidden())
                ? " ORDER BY a.hidden_at DESC, a.id DESC"
                : " ORDER BY a.published_at DESC, a.id DESC";
        return withFilter(jdbcClient.sql(SELECT + where(filter) + order + " LIMIT :limit OFFSET :offset"), filter)
                .param("limit", limit)
                .param("offset", offset)
                .query(ManagedArticleRepository::mapRow)
                .list();
    }

    long count(ArticleFilter filter) {
        return withFilter(
                        jdbcClient.sql("SELECT count(*) FROM articles a JOIN sources s ON s.id = a.source_id "
                                + where(filter)),
                        filter)
                .query(Long.class)
                .single();
    }

    Optional<ManagedArticle> findById(UUID articleId) {
        return jdbcClient
                .sql(SELECT + " WHERE a.id = :articleId")
                .param("articleId", articleId)
                .query(ManagedArticleRepository::mapRow)
                .optional();
    }

    /**
     * Haberin gizli olup olmadığını okur ve satırını işlem bitene kadar kilitler ({@code FOR UPDATE}): aynı
     * haberi aynı anda gizlemeye çalışan ikinci istek bekler ve güncel durumu görür.
     */
    Optional<Boolean> findHiddenForUpdate(UUID articleId) {
        return jdbcClient
                .sql("SELECT hidden FROM articles WHERE id = :articleId FOR UPDATE")
                .param("articleId", articleId)
                .query(Boolean.class)
                .optional();
    }

    void hide(UUID articleId, UUID adminId, String reason) {
        jdbcClient
                .sql("""
				UPDATE articles
				SET hidden = true, hidden_reason = :reason, hidden_at = now(), hidden_by = :adminId
				WHERE id = :articleId
				""")
                .param("articleId", articleId)
                .param("adminId", adminId)
                .param("reason", reason)
                .update();
    }

    /** Gizleme bilgileri de silinir; kimin ne zaman neden gizlediği audit kaydında kalır. */
    void unhide(UUID articleId) {
        jdbcClient.sql("""
				UPDATE articles
				SET hidden = false, hidden_reason = NULL, hidden_at = NULL, hidden_by = NULL
				WHERE id = :articleId
				""").param("articleId", articleId).update();
    }

    /**
     * Filtrelerin SQL'i. Kaynak koşulu yalnızca kaynak seçildiyse eklenir: boş listeyle {@code IN ()} geçersiz
     * olurdu. Değerler her zaman parametre olarak gönderilir; metne yalnızca sabit parçalar eklenir.
     */
    private static String where(ArticleFilter filter) {
        return """
				WHERE (CAST(:hidden AS boolean) IS NULL OR a.hidden = :hidden)
				  AND (CAST(:from AS timestamptz) IS NULL OR a.published_at >= :from)
				  AND (CAST(:to AS timestamptz) IS NULL OR a.published_at <= :to)
				""" + (filter.sourceCodes().isEmpty() ? "" : " AND s.code IN (:sourceCodes)");
    }

    private static JdbcClient.StatementSpec withFilter(JdbcClient.StatementSpec statement, ArticleFilter filter) {
        Timestamp from = filter.from() == null ? null : Timestamp.from(filter.from());
        Timestamp to = filter.to() == null ? null : Timestamp.from(filter.to());
        JdbcClient.StatementSpec spec =
                statement.param("hidden", filter.hidden()).param("from", from).param("to", to);
        return filter.sourceCodes().isEmpty() ? spec : spec.param("sourceCodes", filter.sourceCodes());
    }

    private static ManagedArticle mapRow(ResultSet row, int rowNumber) throws SQLException {
        return new ManagedArticle(
                row.getObject("id", UUID.class),
                row.getString("title"),
                row.getString("url"),
                row.getString("source_code"),
                row.getString("source_name"),
                instant(row, "published_at"),
                row.getBoolean("hidden"),
                instant(row, "hidden_at"),
                row.getString("hidden_reason"),
                row.getObject("hidden_by", UUID.class));
    }
}
