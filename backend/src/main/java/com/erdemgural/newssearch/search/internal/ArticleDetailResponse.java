package com.erdemgural.newssearch.search.internal;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * {@code GET /api/v1/articles/{id}} yanıtı (API sözleşmesi 4.2). Meta veri PostgreSQL'den, özet, tam
 * metin ve yazar Elasticsearch'ten gelir (ADR-0019).
 *
 * @param content tam metin (işçinin temizlediği HTML); kaynak vermiyorsa {@code null}, arayüz özeti
 *     gösterir (FG-AR-06)
 * @param media yalnızca indirilmiş görseller, haberdeki sırasıyla; boşsa arayüz yer tutucu gösterir
 *     (FG-AR-08)
 * @param otherSources aynı haberi yayımlayan diğer kaynaklar; kaynaklar arası gruplama gelene kadar
 *     (İ-28) her zaman boş
 * @param saved haberin bu kullanıcı tarafından kaydedilip kaydedilmediği; kaydedilen haberler
 *     gelene kadar (İ-20) her zaman {@code false}
 */
record ArticleDetailResponse(
        UUID id,
        String title,
        String summary,
        String content,
        String author,
        String url,
        Source source,
        String language,
        String itemType,
        List<String> categories,
        Instant publishedAt,
        List<Media> media,
        List<OtherSource> otherSources,
        boolean saved) {

    /** Kaynak ve atıf bilgisi (FG-AR-07). */
    record Source(String code, String name, String homepageUrl, String attributionText) {}

    /** @param url görsel uç noktasının imzalı adresi */
    record Media(String url, int width, int height, String caption, String credit) {}

    record OtherSource(UUID articleId, OtherSourceName source, String url) {}

    record OtherSourceName(String code, String name) {}
}
