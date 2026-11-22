package com.erdemgural.newssearch.ingestion;

import java.time.Instant;
import java.util.UUID;

/**
 * Yönetim panelindeki bir haber (API sözleşmesi 6.6).
 *
 * @param url haberin kaynağındaki adresi
 * @param hiddenAt gizlenme zamanı; gizli değilse {@code null}
 * @param hiddenReason yöneticinin yazdığı gerekçe; gizli değilse {@code null}
 * @param hiddenBy gizleyen yönetici; gizli değilse {@code null}
 */
public record ManagedArticle(
        UUID id,
        String title,
        String url,
        String sourceCode,
        String sourceName,
        Instant publishedAt,
        boolean hidden,
        Instant hiddenAt,
        String hiddenReason,
        UUID hiddenBy) {}
