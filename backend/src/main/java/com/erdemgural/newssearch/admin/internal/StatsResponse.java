package com.erdemgural.newssearch.admin.internal;

import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * Yönetim panosunun verisi (API sözleşmesi 6.7; FG-YP-12).
 *
 * @param users durumlara göre kullanıcı sayıları ({@code PENDING}, {@code ACTIVE}, {@code PASSIVE},
 *     {@code REJECTED})
 */
record StatsResponse(
        Articles articles, Map<String, Long> users, Feeds feeds, SearchIndex searchIndex, Components components) {

    /** @param last24h son 24 saatte toplanan haberler */
    record Articles(long total, long last24h, List<SourceArticles> bySource) {}

    record SourceArticles(String code, String name, long total, long last24h) {}

    /**
     * @param enabled okunan beslemeler (kendisi ve kaynağı etkin)
     * @param failing okunan beslemelerden son okuması başarısız olanlar
     * @param disabledAuto art arda hatalar yüzünden kendiliğinden kapananlar
     */
    record Feeds(long enabled, long failing, long disabledAuto) {}

    record SearchIndex(long pendingOutboxEvents) {}

    /**
     * Bileşenlerin durumu: {@code UP} veya {@code DOWN}.
     *
     * @param workerLastActivityAt işçinin en son başlattığı okumanın zamanı; hiç okuma yoksa {@code null}
     */
    record Components(String database, String elasticsearch, String objectStorage, Instant workerLastActivityAt) {}
}
