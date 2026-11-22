package com.erdemgural.newssearch.ingestion.internal;

import static com.erdemgural.newssearch.ingestion.internal.ManagedSourceRepository.instant;

import com.erdemgural.newssearch.ingestion.IngestionSummary.SourceArticleCount;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Yönetim panosunun sayıları: haberler, beslemeler ve toplama kayıtları (FG-YP-12). */
@Repository
class IngestionStatisticsRepository {

    record FeedCounts(long enabled, long failing, long autoDisabled) {}

    private final JdbcClient jdbcClient;

    IngestionStatisticsRepository(JdbcClient jdbcClient) {
        this.jdbcClient = jdbcClient;
    }

    /**
     * Kaynak başına haber sayıları, kaynak adına göre. {@code LEFT JOIN}: haberi olmayan kaynak da 0 ile gelir.
     *
     * @param since bu andan sonra toplanan ({@code fetched_at}) haberler ayrıca sayılır
     */
    List<SourceArticleCount> countArticlesBySource(Instant since) {
        return jdbcClient
                .sql("""
				SELECT s.code, s.name,
				       count(a.id) AS total,
				       count(a.id) FILTER (WHERE a.fetched_at >= :since) AS recent
				FROM sources s
				LEFT JOIN articles a ON a.source_id = s.id
				GROUP BY s.id
				ORDER BY s.name
				""")
                .param("since", Timestamp.from(since))
                .query((row, rowNumber) -> new SourceArticleCount(
                        row.getString("code"), row.getString("name"), row.getLong("total"), row.getLong("recent")))
                .list();
    }

    /**
     * Okunan besleme: kendisi ve kaynağı etkin (işçi yalnızca bunları okur). Hatalı: okunan beslemelerden son
     * okuması başarısız olan. Kendiliğinden kapanan: art arda hatalar yüzünden kapanmış ({@code AUTO}).
     */
    FeedCounts countFeeds() {
        return jdbcClient
                .sql("""
				SELECT count(*) FILTER (WHERE f.enabled AND s.enabled) AS enabled,
				       count(*) FILTER (WHERE f.enabled AND s.enabled AND f.consecutive_failures > 0) AS failing,
				       count(*) FILTER (WHERE f.disabled_reason = 'AUTO') AS auto_disabled
				FROM feeds f
				JOIN sources s ON s.id = f.source_id
				""")
                .query((row, rowNumber) ->
                        new FeedCounts(row.getLong("enabled"), row.getLong("failing"), row.getLong("auto_disabled")))
                .single();
    }

    /**
     * En son başlatılan okumanın zamanı ({@code ingestion_runs_started_at_idx} indeksinden okunur). Hiç okuma
     * yoksa (ilk kurulumda işçi henüz çalışmadıysa) boş.
     */
    Optional<Instant> findLastRunStartedAt() {
        return jdbcClient
                .sql("SELECT started_at FROM ingestion_runs ORDER BY started_at DESC LIMIT 1")
                .query((row, rowNumber) -> instant(row, "started_at"))
                .optional();
    }
}
