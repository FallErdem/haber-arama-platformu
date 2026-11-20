package com.erdemgural.newssearch.ingestion;

import java.time.Instant;
import java.util.UUID;

/**
 * Toplama geçmişindeki bir okuma ({@code ingestion_runs}; FG-YP-05, FG-VT-10).
 *
 * @param trigger {@code SCHEDULED} (zamanlayıcı) veya {@code MANUAL} (yönetici istedi)
 * @param status {@code RUNNING}, {@code SUCCEEDED}, {@code NOT_MODIFIED} (kaynak "değişmedi" dedi) veya
 *     {@code FAILED}
 * @param finishedAt okuma sürüyorsa {@code null}
 * @param itemsReceived beslemede gelen haber sayısı = yeni + tekrar + atlanan; başarısız okumada {@code null}
 */
public record IngestionRun(
        UUID id,
        UUID feedId,
        String feedName,
        UUID sourceId,
        String sourceCode,
        String sourceName,
        String trigger,
        String status,
        Instant startedAt,
        Instant finishedAt,
        Integer httpStatus,
        Integer itemsReceived,
        Integer itemsNew,
        Integer itemsDuplicate,
        Integer itemsFailed,
        String errorMessage) {}
