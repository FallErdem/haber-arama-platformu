package com.erdemgural.newssearch.ingestion;

import java.time.Instant;
import java.util.List;

/**
 * Yönetim panelindeki haber listesinin filtreleri; {@code null} veya boş alan filtrelenmez.
 *
 * @param hidden yalnızca gizli ({@code true}) veya yalnızca görünen ({@code false}) haberler
 * @param sourceCodes bu kaynakların haberleri
 * @param from yayın zamanı için alt sınır (dahil)
 * @param to yayın zamanı için üst sınır (dahil)
 */
public record ArticleFilter(Boolean hidden, List<String> sourceCodes, Instant from, Instant to) {

    public ArticleFilter {
        sourceCodes = sourceCodes == null ? List.of() : List.copyOf(sourceCodes);
    }
}
