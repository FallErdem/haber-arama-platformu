package com.erdemgural.newssearch.ingestion;

import java.time.Instant;
import java.util.List;

/**
 * Haber ve besleme sayıları (FG-YP-12).
 *
 * @param bySource kaynaklar, adlarına göre; haberi olmayan kaynak da 0 ile yer alır
 * @param enabledFeeds okunan beslemeler: kendisi ve kaynağı etkin
 * @param failingFeeds okunan beslemelerden son okuması başarısız olanlar
 * @param autoDisabledFeeds art arda hatalar yüzünden kendiliğinden kapanmış beslemeler
 * @param workerLastActivityAt işçinin en son başlattığı okumanın zamanı; hiç okuma yoksa {@code null}. İki
 *     uygulama yalnızca veri depoları üzerinden konuştuğu için işçinin çalıştığı buradan anlaşılır
 */
public record IngestionSummary(
        List<SourceArticleCount> bySource,
        long enabledFeeds,
        long failingFeeds,
        long autoDisabledFeeds,
        Instant workerLastActivityAt) {

    /**
     * Bir kaynağın haber sayıları.
     *
     * @param total gizlenenler dahil bütün haberleri
     * @param recent verilen andan sonra toplananlar ({@code fetched_at})
     */
    public record SourceArticleCount(String code, String name, long total, long recent) {}

    public long totalArticles() {
        return bySource.stream().mapToLong(SourceArticleCount::total).sum();
    }

    public long recentArticles() {
        return bySource.stream().mapToLong(SourceArticleCount::recent).sum();
    }
}
