package com.erdemgural.newssearch.ingestion;

/**
 * Eklenecek kaynak (FG-YP-04). Değerler controller'da doğrulanmıştır; kaynak devre dışı olarak eklenir
 * (ekran akışları 4.3: önce beslemeleri eklenip denenir, sonra etkinleştirilir).
 *
 * @param dailyRequestLimit {@code null}: sınır yok
 * @param license {@code null}: yok
 * @param attributionText {@code null}: yok
 * @param feedTimeZone {@code null}: beslemede yazan saat dilimine güvenilir
 */
public record NewSource(
        String code,
        String name,
        String homepageUrl,
        String readerType,
        String language,
        int requestIntervalSeconds,
        Integer dailyRequestLimit,
        String license,
        String attributionText,
        String feedTimeZone) {}
