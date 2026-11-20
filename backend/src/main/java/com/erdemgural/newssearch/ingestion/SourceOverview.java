package com.erdemgural.newssearch.ingestion;

import java.time.Instant;
import java.util.UUID;

/**
 * Kaynaklar listesindeki bir kaynak ve sağlık özeti (API sözleşmesi 6.2; FG-YP-06).
 *
 * @param failingFeedCount hatalı beslemeler: etkin olup son okuması başarısız olanlar
 *     ({@code consecutive_failures > 0}) ve art arda hatalar yüzünden kendiliğinden kapanmış olanlar
 * @param lastSuccessAt beslemelerinin en son başarılı okuması; hiç okunmadıysa {@code null}
 * @param purgeRequestedAt içerik silme istendiyse isteğin zamanı (FG-YP-14); yoksa {@code null}
 */
public record SourceOverview(
        UUID id,
        String code,
        String name,
        String readerType,
        String language,
        boolean enabled,
        int feedCount,
        int failingFeedCount,
        Instant lastSuccessAt,
        Instant purgeRequestedAt) {}
