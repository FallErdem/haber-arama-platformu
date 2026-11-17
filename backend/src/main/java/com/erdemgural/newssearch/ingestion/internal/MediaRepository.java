package com.erdemgural.newssearch.ingestion.internal;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/**
 * {@code media} tablosunun okunması. Görselleri Python işçisi indirir ve yazar; API yalnızca
 * indirilmiş ({@code DOWNLOADED}) görselleri okur.
 */
@Repository
class MediaRepository {

    /** Gösterilebilir bir görsel: indirilmiş ve haberi gizlenmemiş. */
    record DownloadedMedia(UUID id, UUID articleId, int width, int height, String caption, String credit) {}

    /** Nesne depolamadan okunacak dosyanın yeri ve türü. */
    record StoredFile(String storageKey, String contentType) {}

    private final JdbcClient jdbcClient;

    MediaRepository(JdbcClient jdbcClient) {
        this.jdbcClient = jdbcClient;
    }

    /** Görsel uç noktası için: indirilmiş ve haberi gizlenmemiş görselin dosyası. */
    Optional<StoredFile> findServableFile(UUID mediaId) {
        return jdbcClient
                .sql("""
				SELECT m.storage_key, m.content_type
				FROM media m
				JOIN articles a ON a.id = m.article_id
				WHERE m.id = :mediaId
				  AND m.status = 'DOWNLOADED'
				  AND NOT a.hidden
				""")
                .param("mediaId", mediaId)
                .query((row, rowNumber) -> new StoredFile(row.getString("storage_key"), row.getString("content_type")))
                .optional();
    }

    /** Haber detayı için: haberin indirilmiş görselleri, haberdeki sırasıyla. */
    List<DownloadedMedia> findDownloadedByArticle(UUID articleId) {
        return jdbcClient
                .sql("""
				SELECT id, article_id, width, height, caption, credit
				FROM media
				WHERE article_id = :articleId
				  AND status = 'DOWNLOADED'
				ORDER BY position
				""")
                .param("articleId", articleId)
                .query(MediaRepository::mapRow)
                .list();
    }

    /**
     * Arama sonuçları için: her haberin ana görseli, tek sorguda. Ana görsel indirilememişse sıradaki
     * indirilmiş görsel kullanılır. DISTINCT ON, her haber için ORDER BY'a göre ilk satırı bırakır.
     */
    Map<UUID, DownloadedMedia> findMainImages(Collection<UUID> articleIds) {
        if (articleIds.isEmpty()) {
            return Map.of();
        }
        return jdbcClient.sql("""
				SELECT DISTINCT ON (article_id) id, article_id, width, height, caption, credit
				FROM media
				WHERE article_id IN (:articleIds)
				  AND status = 'DOWNLOADED'
				ORDER BY article_id, position
				""").param("articleIds", articleIds).query(MediaRepository::mapRow).list().stream()
                .collect(Collectors.toMap(DownloadedMedia::articleId, Function.identity()));
    }

    private static DownloadedMedia mapRow(java.sql.ResultSet row, int rowNumber) throws java.sql.SQLException {
        return new DownloadedMedia(
                row.getObject("id", UUID.class),
                row.getObject("article_id", UUID.class),
                row.getInt("width"),
                row.getInt("height"),
                row.getString("caption"),
                row.getString("credit"));
    }
}
