package com.erdemgural.newssearch.ingestion;

import java.util.Optional;

/**
 * Kaynakta yapılacak değişiklik (FG-YP-04). Yalnızca istekte gönderilen alanlar değişir (sözleşme 2.5).
 *
 * <p>Alanların anlamı:
 *
 * <ul>
 *   <li>Boş bırakılamayan alanlar ({@code name}, {@code homepageUrl}, {@code requestIntervalSeconds},
 *       {@code enabled}): {@code null} ise değişmez.
 *   <li>Boş bırakılabilen alanlar ({@code Optional}): {@code null} ise değişmez, {@code Optional.empty()} ise
 *       boşaltılır, değer varsa o değer yazılır. Bu ayrım gerekir, çünkü "alan gönderilmedi" ile "alan boş
 *       olsun" iki farklı istektir.
 * </ul>
 *
 * @param version istemcinin gördüğü kaydın sürümü; kayıt bu arada değiştiyse istek reddedilir
 */
public record SourceChange(
        String name,
        String homepageUrl,
        Integer requestIntervalSeconds,
        Optional<Integer> dailyRequestLimit,
        Optional<String> license,
        Optional<String> attributionText,
        Optional<String> feedTimeZone,
        Boolean enabled,
        int version) {}
