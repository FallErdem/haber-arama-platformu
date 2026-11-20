package com.erdemgural.newssearch.ingestion;

import java.time.Instant;
import java.util.UUID;

/**
 * Toplama geçmişinin filtreleri; {@code null} alan filtrelenmez.
 *
 * @param from okumanın başlangıcı için alt sınır (dahil)
 * @param to okumanın başlangıcı için üst sınır (dahil)
 */
public record IngestionRunFilter(UUID sourceId, UUID feedId, String status, Instant from, Instant to) {}
