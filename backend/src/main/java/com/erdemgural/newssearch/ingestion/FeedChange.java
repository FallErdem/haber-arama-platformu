package com.erdemgural.newssearch.ingestion;

import java.util.Optional;

/**
 * Beslemede yapılacak değişiklik. Alanların anlamı {@link SourceChange} ile aynıdır: {@code null} değişmez;
 * boş bırakılabilen {@code defaultCategoryCode} için {@code Optional.empty()} boşaltır.
 *
 * @param enabled {@code true}: etkinleştirir (otomatik kapanmışsa hata sayacı da sıfırlanır), besleme
 *     hemen okunur; {@code false}: devre dışı bırakır (neden {@code MANUAL})
 * @param version istemcinin gördüğü kaydın sürümü
 */
public record FeedChange(
        String name,
        String url,
        Optional<String> defaultCategoryCode,
        Boolean useItemCategories,
        Integer fetchIntervalMinutes,
        Boolean enabled,
        int version) {}
