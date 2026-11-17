package com.erdemgural.newssearch.search.internal;

import com.fasterxml.jackson.annotation.JsonInclude;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Arama sonucundaki bir haber (API sözleşmesi 4.1).
 *
 * @param highlights eşleşen kelimeleri {@code <mark>} ile işaretlenmiş başlık ve özet; arama
 *     ifadesi yoksa yanıtta bulunmaz
 * @param image haberin ana görseli; görsel uç noktası gelene kadar (İ-18) her zaman {@code null},
 *     arayüz yer tutucu gösterir
 * @param otherSourcesCount aynı haberi yayımlayan diğer kaynakların sayısı; kaynaklar arası
 *     gruplama gelene kadar (İ-28) her zaman 0
 */
record ArticleSearchItem(
        UUID id,
        String title,
        @JsonInclude(JsonInclude.Include.NON_NULL) Map<String, List<String>> highlights,
        String summary,
        Source source,
        String language,
        String itemType,
        List<String> categories,
        Instant publishedAt,
        String url,
        Image image,
        int otherSourcesCount) {

    record Source(String code, String name) {}

    record Image(String url, int width, int height) {}
}
