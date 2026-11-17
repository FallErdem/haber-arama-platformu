package com.erdemgural.newssearch.ingestion;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * Bir haberin listelerde gösterilen bilgileri. Arama indeksi yalnızca haberin kimliğini verir;
 * gösterilecek bilgiler asıl kayıttan (PostgreSQL) okunur.
 *
 * @param categories kategori kodları, arayüzdeki sırayla
 * @param image haberin ana görseli (indirilmiş görsellerden sırası en küçük olan); yoksa {@code null}
 */
public record ArticleSummary(
        UUID id,
        String title,
        String summary,
        String sourceCode,
        String sourceName,
        String language,
        String itemType,
        List<String> categories,
        Instant publishedAt,
        String url,
        ArticleImage image) {

    /** Aynı haberin, ana görseli eklenmiş kopyası (kayıt değişmez olduğu için yeni nesne). */
    public ArticleSummary withImage(ArticleImage image) {
        return new ArticleSummary(
                id, title, summary, sourceCode, sourceName, language, itemType, categories, publishedAt, url, image);
    }
}
