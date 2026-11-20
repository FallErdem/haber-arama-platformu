package com.erdemgural.newssearch.ingestion.internal;

import static com.erdemgural.newssearch.ingestion.internal.ManagedSourceRepository.instant;

import com.erdemgural.newssearch.ingestion.ManagedFeed;
import com.erdemgural.newssearch.ingestion.NewFeed;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/**
 * Yönetim panelinin {@code feeds} sorguları (FG-YP-04, FG-YP-06 – 08). Okuma zamanı, hata sayacı ve
 * koşullu istek değerleri gibi sağlık alanlarını işçi yazar; burada yalnızca yöneticinin işlemleri vardır.
 */
@Repository
class ManagedFeedRepository {

    /**
     * Beslemenin yönetici tarafından değiştirilebilen ayarları, değişiklik uygulandıktan sonraki halleriyle.
     *
     * @param urlChanged adres değiştiyse saklanan koşullu istek değerleri (ETag, Last-Modified) silinir: eski
     *     adresin değerleri yeni adrese gönderilmemeli
     * @param reenabled devre dışı besleme etkinleştirildiyse hemen okunur
     * @param resetFailures otomatik kapanmış besleme etkinleştirildiyse art arda hata sayacı sıfırlanır
     */
    record FeedSettings(
            String name,
            String url,
            String defaultCategoryCode,
            boolean useItemCategories,
            int fetchIntervalMinutes,
            boolean enabled,
            String disabledReason,
            boolean urlChanged,
            boolean reenabled,
            boolean resetFailures) {}

    private static final String SELECT = """
			SELECT f.id, f.source_id, f.name, f.url, c.code AS default_category_code, f.use_item_categories,
			       f.fetch_interval_minutes, f.enabled, f.disabled_reason, f.consecutive_failures,
			       f.last_success_at, f.last_error, f.next_fetch_at, f.manual_fetch_requested_at, f.version
			FROM feeds f
			LEFT JOIN categories c ON c.id = f.default_category_id
			""";

    private final JdbcClient jdbcClient;

    ManagedFeedRepository(JdbcClient jdbcClient) {
        this.jdbcClient = jdbcClient;
    }

    List<ManagedFeed> findBySource(UUID sourceId) {
        return jdbcClient
                .sql(SELECT + " WHERE f.source_id = :sourceId ORDER BY f.name")
                .param("sourceId", sourceId)
                .query(ManagedFeedRepository::mapRow)
                .list();
    }

    Optional<ManagedFeed> findById(UUID feedId) {
        return jdbcClient
                .sql(SELECT + " WHERE f.id = :feedId")
                .param("feedId", feedId)
                .query(ManagedFeedRepository::mapRow)
                .optional();
    }

    /**
     * Beslemeyi okur ve satırını kilitler. İşçi de sonucu yazarken aynı satırı kilitler; yönetici beslemeyi
     * değiştirirken işçinin yazması beklenir ({@code OF f}: yalnızca beslemenin satırı kilitlenir).
     */
    Optional<ManagedFeed> findForUpdate(UUID feedId) {
        return jdbcClient
                .sql(SELECT + " WHERE f.id = :feedId FOR UPDATE OF f")
                .param("feedId", feedId)
                .query(ManagedFeedRepository::mapRow)
                .optional();
    }

    /**
     * Beslemeyi etkin olarak ekler ve kimliğini döner. Okuma zamanı tablonun varsayılanıyla şimdidir; kaynak
     * etkinse işçi beslemeyi bir sonraki turda okur. Adres veya kaynak içinde ad zaten varsa
     * {@code DuplicateKeyException}.
     */
    UUID insert(UUID sourceId, NewFeed feed) {
        return jdbcClient
                .sql("""
				INSERT INTO feeds (source_id, name, url, default_category_id, use_item_categories, fetch_interval_minutes)
				VALUES (:sourceId, :name, :url, (SELECT id FROM categories WHERE code = :categoryCode),
				        :useItemCategories, :fetchIntervalMinutes)
				RETURNING id
				""")
                .param("sourceId", sourceId)
                .param("name", feed.name())
                .param("url", feed.url())
                .param("categoryCode", feed.defaultCategoryCode())
                .param("useItemCategories", feed.useItemCategories())
                .param("fetchIntervalMinutes", feed.fetchIntervalMinutes())
                .query(UUID.class)
                .single();
    }

    /** Ayarları yazar ve sürümü bir artırır. Sağlık alanlarına yalnızca {@link FeedSettings}'teki bayraklar dokunur. */
    void update(UUID feedId, FeedSettings settings) {
        jdbcClient
                .sql("""
				UPDATE feeds
				SET name = :name,
				    url = :url,
				    default_category_id = (SELECT id FROM categories WHERE code = :categoryCode),
				    use_item_categories = :useItemCategories,
				    fetch_interval_minutes = :fetchIntervalMinutes,
				    enabled = :enabled,
				    disabled_reason = :disabledReason,
				    etag = CASE WHEN :urlChanged THEN NULL ELSE etag END,
				    last_modified = CASE WHEN :urlChanged THEN NULL ELSE last_modified END,
				    next_fetch_at = CASE WHEN :reenabled THEN now() ELSE next_fetch_at END,
				    consecutive_failures = CASE WHEN :resetFailures THEN 0 ELSE consecutive_failures END,
				    version = version + 1
				WHERE id = :feedId
				""")
                .param("feedId", feedId)
                .param("name", settings.name())
                .param("url", settings.url())
                .param("categoryCode", settings.defaultCategoryCode())
                .param("useItemCategories", settings.useItemCategories())
                .param("fetchIntervalMinutes", settings.fetchIntervalMinutes())
                .param("enabled", settings.enabled())
                .param("disabledReason", settings.disabledReason())
                .param("urlChanged", settings.urlChanged())
                .param("reenabled", settings.reenabled())
                .param("resetFailures", settings.resetFailures())
                .update();
    }

    /**
     * Elle toplama (FG-YP-08): kaynağın etkin beslemelerini hemen okunacak hale getirir ve isteğin zamanını
     * yazar; işçi okumayı {@code MANUAL} olarak kaydeder (V16). İki uygulama doğrudan konuşmadığı için istek
     * tabloda taşınır.
     *
     * @return okunacak besleme sayısı
     */
    int requestFetch(UUID sourceId) {
        return jdbcClient.sql("""
				UPDATE feeds
				SET manual_fetch_requested_at = now(),
				    next_fetch_at = now()
				WHERE source_id = :sourceId
				  AND enabled
				""").param("sourceId", sourceId).update();
    }

    boolean categoryExists(String code) {
        return jdbcClient
                .sql("SELECT EXISTS (SELECT 1 FROM categories WHERE code = :code)")
                .param("code", code)
                .query(Boolean.class)
                .single();
    }

    private static ManagedFeed mapRow(ResultSet row, int rowNumber) throws SQLException {
        return new ManagedFeed(
                row.getObject("id", UUID.class),
                row.getObject("source_id", UUID.class),
                row.getString("name"),
                row.getString("url"),
                row.getString("default_category_code"),
                row.getBoolean("use_item_categories"),
                row.getInt("fetch_interval_minutes"),
                row.getBoolean("enabled"),
                row.getString("disabled_reason"),
                row.getInt("consecutive_failures"),
                instant(row, "last_success_at"),
                row.getString("last_error"),
                instant(row, "next_fetch_at"),
                instant(row, "manual_fetch_requested_at"),
                row.getInt("version"));
    }
}
