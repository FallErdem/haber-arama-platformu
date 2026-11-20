package com.erdemgural.newssearch.ingestion;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * Yönetim panelindeki bir kaynak: ayarları ve beslemeleri (API sözleşmesi 6.2).
 *
 * @param code kaynağın kodu ({@code TRT}); eklendikten sonra değiştirilemez
 * @param readerType okuyucu türü ({@code RSS}, {@code ATOM}); eklendikten sonra değiştirilemez
 * @param language {@code tr} veya {@code en}; eklendikten sonra değiştirilemez
 * @param requestIntervalSeconds aynı kaynağa iki istek arasında beklenecek süre (FG-VT-05)
 * @param dailyRequestLimit son 24 saatteki en fazla istek sayısı; {@code null} ise sınır yok
 * @param feedTimeZone beslemedeki saatlerin gerçekte yazıldığı saat dilimi (ör. {@code Europe/Istanbul});
 *     {@code null} ise beslemede yazan saat dilimine güvenilir
 * @param version iyimser kilitleme sürümü (sözleşme 2.5)
 * @param feeds beslemeleri, adlarına göre sıralı
 */
public record ManagedSource(
        UUID id,
        String code,
        String name,
        String homepageUrl,
        String readerType,
        String language,
        int requestIntervalSeconds,
        Integer dailyRequestLimit,
        String license,
        String attributionText,
        String feedTimeZone,
        boolean enabled,
        Instant purgeRequestedAt,
        int version,
        List<ManagedFeed> feeds) {}
