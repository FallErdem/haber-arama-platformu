package com.erdemgural.newssearch.ingestion.internal;

import com.erdemgural.newssearch.ingestion.ManagedSource;
import com.erdemgural.newssearch.ingestion.NewSource;
import com.erdemgural.newssearch.ingestion.SourceOverview;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Yönetim panelinin {@code sources} sorguları (FG-YP-04, FG-YP-06). */
@Repository
class ManagedSourceRepository {

    /** Kaynağın yönetici tarafından değiştirilebilen ayarları; değişiklik uygulandıktan sonraki halleri. */
    record SourceSettings(
            String name,
            String homepageUrl,
            int requestIntervalSeconds,
            Integer dailyRequestLimit,
            String license,
            String attributionText,
            String feedTimeZone,
            boolean enabled) {}

    private static final String COLUMNS = """
			id, code, name, homepage_url, reader_type, language, request_interval_seconds, daily_request_limit,
			license, attribution_text, feed_time_zone, enabled, purge_requested_at, version""";

    private final JdbcClient jdbcClient;

    ManagedSourceRepository(JdbcClient jdbcClient) {
        this.jdbcClient = jdbcClient;
    }

    /**
     * Kaynaklar ve sağlık özetleri. Hatalı besleme: etkin olup son okuması başarısız olan ya da art arda
     * hatalar yüzünden kendiliğinden kapanmış besleme. Elle kapatılmış beslemenin eski hataları sayılmaz.
     */
    List<SourceOverview> findOverviews() {
        return jdbcClient
                .sql("""
				SELECT s.id, s.code, s.name, s.reader_type, s.language, s.enabled, s.purge_requested_at,
				       count(f.id) AS feed_count,
				       count(f.id) FILTER (
				           WHERE (f.enabled AND f.consecutive_failures > 0) OR f.disabled_reason = 'AUTO'
				       ) AS failing_feed_count,
				       max(f.last_success_at) AS last_success_at
				FROM sources s
				LEFT JOIN feeds f ON f.source_id = s.id
				GROUP BY s.id
				ORDER BY s.name
				""")
                .query((row, rowNumber) -> new SourceOverview(
                        row.getObject("id", UUID.class),
                        row.getString("code"),
                        row.getString("name"),
                        row.getString("reader_type"),
                        row.getString("language"),
                        row.getBoolean("enabled"),
                        row.getInt("feed_count"),
                        row.getInt("failing_feed_count"),
                        instant(row, "last_success_at"),
                        instant(row, "purge_requested_at")))
                .list();
    }

    /** Kaynak, beslemeleri olmadan ({@code feeds} boş liste). */
    Optional<ManagedSource> findById(UUID sourceId) {
        return jdbcClient
                .sql("SELECT " + COLUMNS + " FROM sources WHERE id = :sourceId")
                .param("sourceId", sourceId)
                .query(ManagedSourceRepository::mapRow)
                .optional();
    }

    /**
     * Kaynağı okur ve satırını işlem bitene kadar kilitler ({@code FOR UPDATE}); aynı kaynağı aynı anda
     * değiştirmeye çalışan diğer istek bekler.
     */
    Optional<ManagedSource> findForUpdate(UUID sourceId) {
        return jdbcClient
                .sql("SELECT " + COLUMNS + " FROM sources WHERE id = :sourceId FOR UPDATE")
                .param("sourceId", sourceId)
                .query(ManagedSourceRepository::mapRow)
                .optional();
    }

    /**
     * Kaynağı devre dışı olarak ekler ve kimliğini döner. Kod veya ad zaten varsa veritabanının benzersizlik
     * kuralı {@code DuplicateKeyException} fırlatır.
     */
    UUID insert(NewSource source) {
        return jdbcClient
                .sql("""
				INSERT INTO sources (
				    code, name, homepage_url, reader_type, language, request_interval_seconds,
				    daily_request_limit, license, attribution_text, feed_time_zone, enabled)
				VALUES (
				    :code, :name, :homepageUrl, :readerType, :language, :requestIntervalSeconds,
				    :dailyRequestLimit, :license, :attributionText, :feedTimeZone, false)
				RETURNING id
				""")
                .param("code", source.code())
                .param("name", source.name())
                .param("homepageUrl", source.homepageUrl())
                .param("readerType", source.readerType())
                .param("language", source.language())
                .param("requestIntervalSeconds", source.requestIntervalSeconds())
                .param("dailyRequestLimit", source.dailyRequestLimit())
                .param("license", source.license())
                .param("attributionText", source.attributionText())
                .param("feedTimeZone", source.feedTimeZone())
                .query(UUID.class)
                .single();
    }

    /** Değiştirilebilen bütün ayarları yazar ve sürümü bir artırır. */
    void update(UUID sourceId, SourceSettings settings) {
        jdbcClient
                .sql("""
				UPDATE sources
				SET name = :name,
				    homepage_url = :homepageUrl,
				    request_interval_seconds = :requestIntervalSeconds,
				    daily_request_limit = :dailyRequestLimit,
				    license = :license,
				    attribution_text = :attributionText,
				    feed_time_zone = :feedTimeZone,
				    enabled = :enabled,
				    version = version + 1
				WHERE id = :sourceId
				""")
                .param("sourceId", sourceId)
                .param("name", settings.name())
                .param("homepageUrl", settings.homepageUrl())
                .param("requestIntervalSeconds", settings.requestIntervalSeconds())
                .param("dailyRequestLimit", settings.dailyRequestLimit())
                .param("license", settings.license())
                .param("attributionText", settings.attributionText())
                .param("feedTimeZone", settings.feedTimeZone())
                .param("enabled", settings.enabled())
                .update();
    }

    /** Kaynağın haber sayısı ({@code articles_source_id_published_at_idx} indeksinden sayılır). */
    long countArticles(UUID sourceId) {
        return jdbcClient
                .sql("SELECT count(*) FROM articles WHERE source_id = :sourceId")
                .param("sourceId", sourceId)
                .query(Long.class)
                .single();
    }

    /**
     * İçeriğin silinmesini ister: işçi {@code purge_requested_at} dolu kaynakların haberlerini siler ve
     * bitirince alanı boşaltır (FG-YP-14). Kaynağın durumu değiştiği için sürüm de artar.
     */
    void requestPurge(UUID sourceId) {
        jdbcClient
                .sql("UPDATE sources SET purge_requested_at = now(), version = version + 1 WHERE id = :sourceId")
                .param("sourceId", sourceId)
                .update();
    }

    private static ManagedSource mapRow(ResultSet row, int rowNumber) throws SQLException {
        return new ManagedSource(
                row.getObject("id", UUID.class),
                row.getString("code"),
                row.getString("name"),
                row.getString("homepage_url"),
                row.getString("reader_type"),
                row.getString("language"),
                row.getInt("request_interval_seconds"),
                row.getObject("daily_request_limit", Integer.class),
                row.getString("license"),
                row.getString("attribution_text"),
                row.getString("feed_time_zone"),
                row.getBoolean("enabled"),
                instant(row, "purge_requested_at"),
                row.getInt("version"),
                // Haber sayısı ve beslemeler detayda ayrı sorgularla doldurulur (SourceAdministrationService).
                0,
                List.of());
    }

    static Instant instant(ResultSet row, String column) throws SQLException {
        Timestamp timestamp = row.getTimestamp(column);
        return timestamp == null ? null : timestamp.toInstant();
    }
}
