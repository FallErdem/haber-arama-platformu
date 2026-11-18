package com.erdemgural.newssearch.ingestion;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * Haber detayının PostgreSQL'deki kısmı: meta veri, kaynak ve atıf bilgisi, indirilmiş görseller.
 * Özet, tam metin ve yazar bu kayıtta yoktur; tek kayıtları Elasticsearch'tir (ADR-0019) ve detayı
 * sunan {@code search} modülü onları oradan okur.
 *
 * @param categories kategori kodları, arayüzdeki sırayla; süreli kategoriler henüz ayıklanmamıştır
 *     ({@link CategoryWindows})
 * @param media indirilmiş görseller, haberdeki sırasıyla; adresleri imzalıdır
 */
public record ArticleDetails(
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
        Instant publishedAt,
        List<ArticleMedia> media) {

    /** Haberin bir görseli; {@code url} görsel uç noktasının imzalı adresidir (API sözleşmesi 4.4). */
    public record ArticleMedia(String url, int width, int height, String caption, String credit) {}
}
