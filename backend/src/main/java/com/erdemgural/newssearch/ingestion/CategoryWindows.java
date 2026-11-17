package com.erdemgural.newssearch.ingestion;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;

/** Süreli kategorilerin kuralı (FG-AR-12); arama sonuçları ve haber detayı aynı kuralı kullanır. */
public final class CategoryWindows {

    private CategoryWindows() {}

    /**
     * Haberin şu an geçerli kategorileri. Süreli bir kategori (Son Dakika) süresi dolmuş haberde
     * gösterilmez; haber konu kategorileriyle görünmeye devam eder.
     *
     * @param windows süreli kategoriler ve süreleri ({@link CategoryCatalog#timeWindows()})
     */
    public static List<String> current(
            List<String> categories, Instant publishedAt, Map<String, Duration> windows, Instant now) {
        return categories.stream()
                .filter(code -> {
                    Duration window = windows.get(code);
                    return window == null || publishedAt.isAfter(now.minus(window));
                })
                .toList();
    }
}
