package com.erdemgural.newssearch.audit;

import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

/**
 * Audit kayıtlarının filtreleri (API sözleşmesi 6.8); {@code null} alan filtrelenmez.
 *
 * <p>Alt ve üst sınır her zaman vardır: tablo aylara bölümlenmiştir ve sorgu yalnızca aralığa düşen bölümlere
 * bakar. Varsayılanları (son 30 gün, üst sınır şimdi) isteği okuyan taraf belirler.
 *
 * @param action işlem kodu; API'nin ve işçinin kodları ({@code FEED_AUTO_DISABLED} gibi) birlikte aranır
 * @param targetType hedefin türü ({@link AuditTargetType} adlarından biri)
 * @param result {@code SUCCESS} veya {@code FAILURE}
 * @param from kaydın zamanı için alt sınır (dahil)
 * @param to kaydın zamanı için üst sınır (dahil)
 */
public record AuditEventFilter(
        UUID actorUserId, String action, String targetType, UUID targetId, String result, Instant from, Instant to) {

    public AuditEventFilter {
        Objects.requireNonNull(from, "from");
        Objects.requireNonNull(to, "to");
    }
}
