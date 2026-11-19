package com.erdemgural.newssearch.library.internal;

import java.time.Instant;
import java.util.UUID;

/**
 * Kaydedilen haberler listesindeki bir öğe (API sözleşmesi 5.1).
 *
 * @param hidden haber kaydedildikten sonra yönetici tarafından gizlendiyse {@code true} (FG-KO-03)
 * @param article haberin listede gösterilen bilgisi; gizlenmiş haberde {@code null}, arayüz haberin
 *     kaldırıldığını gösterir
 */
record SavedArticleItem(UUID articleId, Instant savedAt, boolean hidden, Article article) {

    /** @param image haberin ana görseli; yoksa {@code null}, arayüz yer tutucu gösterir (FG-AR-08) */
    record Article(String title, Source source, Instant publishedAt, Image image) {}

    record Source(String code, String name) {}

    /** @param url görsel uç noktasının imzalı adresi (sözleşme 4.4) */
    record Image(String url, int width, int height) {}
}
