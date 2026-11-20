package com.erdemgural.newssearch.ingestion;

import java.time.Instant;
import java.util.UUID;

/**
 * Yönetim panelindeki bir besleme: ayarları ve sağlık durumu (API sözleşmesi 6.3; FG-YP-06, FG-YP-07).
 *
 * @param defaultCategoryCode besleme düzeyindeki kategori; karışık içerikli beslemede {@code null}
 * @param disabledReason devre dışıysa nedeni: {@code MANUAL} (yönetici kapattı) veya {@code AUTO} (art arda
 *     hatalar yüzünden kendiliğinden kapandı); etkinse {@code null}
 * @param consecutiveFailures art arda başarısız okuma sayısı; başarılı okumada sıfırlanır
 * @param manualFetchRequestedAt elle toplama istendiyse ve henüz okunmadıysa isteğin zamanı
 * @param version iyimser kilitleme sürümü (sözleşme 2.5); yönetici her değiştirdiğinde artar. İşçinin
 *     yazdığı sağlık alanları sürümü değiştirmez
 */
public record ManagedFeed(
        UUID id,
        UUID sourceId,
        String name,
        String url,
        String defaultCategoryCode,
        boolean useItemCategories,
        int fetchIntervalMinutes,
        boolean enabled,
        String disabledReason,
        int consecutiveFailures,
        Instant lastSuccessAt,
        String lastError,
        Instant nextFetchAt,
        Instant manualFetchRequestedAt,
        int version) {}
