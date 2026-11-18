package com.erdemgural.newssearch.search.internal;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Elasticsearch'ten dönen sonuç: sıralı haber kimlikleri, özetler ve vurgular.
 *
 * @param total eşleşen haber sayısı; en fazla 10.000'e kadar sayılır
 * @param totalIsExact {@code false} ise gerçek sayı {@code total} değerinden büyük olabilir
 */
record SearchHits(List<Hit> hits, long total, boolean totalIsExact) {

    /**
     * @param summary haberin özeti; tek kaydı Elasticsearch'tir (ADR-0019). Özeti yoksa {@code null}
     * @param highlights alan adına göre vurgulanmış metinler (örnek anahtar: {@code title_tr})
     */
    record Hit(UUID articleId, String summary, Map<String, List<String>> highlights) {}
}
