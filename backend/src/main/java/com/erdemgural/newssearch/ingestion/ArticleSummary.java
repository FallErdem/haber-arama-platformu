package com.erdemgural.newssearch.ingestion;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * Bir haberin listelerde gösterilen bilgileri. Arama indeksi yalnızca haberin kimliğini verir;
 * gösterilecek bilgiler asıl kayıttan (PostgreSQL) okunur.
 *
 * @param categories kategori kodları, arayüzdeki sırayla
 */
public record ArticleSummary(
        UUID id,
        String title,
        String summary,
        String sourceCode,
        String sourceName,
        String language,
        String itemType,
        List<String> categories,
        Instant publishedAt,
        String url) {}
