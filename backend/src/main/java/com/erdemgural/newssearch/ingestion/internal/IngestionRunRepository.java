package com.erdemgural.newssearch.ingestion.internal;

import static com.erdemgural.newssearch.ingestion.internal.ManagedSourceRepository.instant;

import com.erdemgural.newssearch.ingestion.IngestionRun;
import com.erdemgural.newssearch.ingestion.IngestionRunFilter;
import java.sql.Timestamp;
import java.util.List;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** {@code ingestion_runs} okuma (FG-YP-05). Kayıtları işçi yazar. */
@Repository
class IngestionRunRepository {

    /**
     * Filtreler: verilmeyen ({@code null}) filtre koşulu her satırda doğrudur. {@code CAST}: PostgreSQL, yalnızca
     * {@code IS NULL} ile karşılaştırılan bir parametrenin türünü kendisi çıkaramaz.
     */
    private static final String FROM_WHERE = """
			FROM ingestion_runs r
			JOIN feeds f ON f.id = r.feed_id
			JOIN sources s ON s.id = f.source_id
			WHERE (CAST(:sourceId AS uuid) IS NULL OR f.source_id = :sourceId)
			  AND (CAST(:feedId AS uuid) IS NULL OR r.feed_id = :feedId)
			  AND (CAST(:status AS text) IS NULL OR r.status = :status)
			  AND (CAST(:from AS timestamptz) IS NULL OR r.started_at >= :from)
			  AND (CAST(:to AS timestamptz) IS NULL OR r.started_at <= :to)
			""";

    private final JdbcClient jdbcClient;

    IngestionRunRepository(JdbcClient jdbcClient) {
        this.jdbcClient = jdbcClient;
    }

    /** Okumalardan bir sayfa, yeniden eskiye; aynı anda başlayanların sırası kimlikle sabitlenir. */
    List<IngestionRun> findPage(IngestionRunFilter filter, int limit, long offset) {
        return withFilter(
                        jdbcClient.sql("""
						SELECT r.id, r.feed_id, f.name AS feed_name, s.id AS source_id, s.code AS source_code,
						       s.name AS source_name, r.trigger, r.status, r.started_at, r.finished_at, r.http_status,
						       r.items_received, r.items_new, r.items_duplicate, r.items_failed, r.error_message
						""" + FROM_WHERE
                                + " ORDER BY r.started_at DESC, r.id DESC LIMIT :limit OFFSET :offset"),
                        filter)
                .param("limit", limit)
                .param("offset", offset)
                .query((row, rowNumber) -> new IngestionRun(
                        row.getObject("id", UUID.class),
                        row.getObject("feed_id", UUID.class),
                        row.getString("feed_name"),
                        row.getObject("source_id", UUID.class),
                        row.getString("source_code"),
                        row.getString("source_name"),
                        row.getString("trigger"),
                        row.getString("status"),
                        instant(row, "started_at"),
                        instant(row, "finished_at"),
                        row.getObject("http_status", Integer.class),
                        row.getObject("items_received", Integer.class),
                        row.getObject("items_new", Integer.class),
                        row.getObject("items_duplicate", Integer.class),
                        row.getObject("items_failed", Integer.class),
                        row.getString("error_message")))
                .list();
    }

    long count(IngestionRunFilter filter) {
        return withFilter(jdbcClient.sql("SELECT count(*) " + FROM_WHERE), filter)
                .query(Long.class)
                .single();
    }

    private static JdbcClient.StatementSpec withFilter(JdbcClient.StatementSpec statement, IngestionRunFilter filter) {
        // Zaman parametreleri, projedeki diğer sorgulardaki gibi Timestamp olarak verilir.
        Timestamp from = filter.from() == null ? null : Timestamp.from(filter.from());
        Timestamp to = filter.to() == null ? null : Timestamp.from(filter.to());
        return statement
                .param("sourceId", filter.sourceId())
                .param("feedId", filter.feedId())
                .param("status", filter.status())
                .param("from", from)
                .param("to", to);
    }
}
