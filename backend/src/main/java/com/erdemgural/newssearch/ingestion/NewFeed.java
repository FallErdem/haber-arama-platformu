package com.erdemgural.newssearch.ingestion;

/**
 * Kaynağa eklenecek besleme (FG-YP-04). Besleme etkin eklenir ve okuma zamanı hemen gelmiş olur; kaynak
 * etkinse işçi onu bir sonraki turda okur (sözleşme 6.3).
 *
 * @param defaultCategoryCode besleme düzeyindeki kategori; karışık içerikli beslemede {@code null}
 * @param useItemCategories haberlerin kendi kategori değerleri eşleme tablosuyla çevrilsin mi
 */
public record NewFeed(
        String name, String url, String defaultCategoryCode, boolean useItemCategories, int fetchIntervalMinutes) {}
