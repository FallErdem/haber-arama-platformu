package com.erdemgural.newssearch.library.internal;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** {@code saved_articles} tablosu (veri modeli, V7). Kayıtlar her zaman bir kullanıcıya göre okunur. */
@Repository
class SavedArticleRepository {

    /** Bir kaydedilen haber: hangi haber, ne zaman kaydedildi. */
    record SavedArticleRow(UUID articleId, Instant savedAt) {}

    private final JdbcClient jdbcClient;

    SavedArticleRepository(JdbcClient jdbcClient) {
        this.jdbcClient = jdbcClient;
    }

    /**
     * Haberi kaydeder. Zaten kayıtlıysa bir şey değişmez; kaydedilme zamanı da ilk kaydedildiği an
     * olarak kalır. {@code ON CONFLICT}: aynı anda gelen iki istek de hatasız biter.
     */
    void save(UUID userId, UUID articleId) {
        jdbcClient
                .sql("""
				INSERT INTO saved_articles (user_id, article_id)
				VALUES (:userId, :articleId)
				ON CONFLICT (user_id, article_id) DO NOTHING
				""")
                .param("userId", userId)
                .param("articleId", articleId)
                .update();
    }

    /** Kayıttan çıkarır. Kayıtlı değilse bir şey değişmez. */
    void delete(UUID userId, UUID articleId) {
        jdbcClient
                .sql("DELETE FROM saved_articles WHERE user_id = :userId AND article_id = :articleId")
                .param("userId", userId)
                .param("articleId", articleId)
                .update();
    }

    boolean exists(UUID userId, UUID articleId) {
        return jdbcClient
                .sql("""
				SELECT EXISTS (
				    SELECT 1 FROM saved_articles WHERE user_id = :userId AND article_id = :articleId)
				""")
                .param("userId", userId)
                .param("articleId", articleId)
                .query(Boolean.class)
                .single();
    }

    /**
     * Kullanıcının kayıtlarından bir sayfa, yeniden eskiye. Aynı anda kaydedilen haberlerin sırası
     * haber kimliğiyle sabitlenir; yoksa sayfalar arasında bir haber iki kez görünebilir veya hiç
     * görünmeyebilir.
     */
    List<SavedArticleRow> findPage(UUID userId, int limit, long offset) {
        return jdbcClient
                .sql("""
				SELECT article_id, created_at
				FROM saved_articles
				WHERE user_id = :userId
				ORDER BY created_at DESC, article_id DESC
				LIMIT :limit OFFSET :offset
				""")
                .param("userId", userId)
                .param("limit", limit)
                .param("offset", offset)
                .query((row, rowNumber) -> new SavedArticleRow(
                        row.getObject("article_id", UUID.class),
                        row.getTimestamp("created_at").toInstant()))
                .list();
    }

    long count(UUID userId) {
        return jdbcClient
                .sql("SELECT count(*) FROM saved_articles WHERE user_id = :userId")
                .param("userId", userId)
                .query(Long.class)
                .single();
    }
}
