package com.erdemgural.newssearch.market.internal;

import java.math.BigDecimal;
import java.time.Instant;

/**
 * {@code GET /api/v1/market-quotes} yanıtındaki bir değer. Görünen ad ("Dolar", "Gram altın") burada yoktur;
 * arayüz adı kendi dil dosyalarından koda göre bulur.
 *
 * @param code {@code USD}, {@code EUR}, {@code GRAM_GOLD}, {@code GOLD_OUNCE}, {@code SILVER_OUNCE}, {@code BIST100},
 *     {@code BRENT} veya {@code BITCOIN}
 * @param changePercent önceki kapanışa göre değişim yüzdesi, iki basamağa yuvarlanmış ({@code 0.13} = %0,13)
 * @param currency fiyatın para birimi: {@code TRY} veya {@code USD}
 * @param marketTime piyasadaki son fiyatın zamanı
 * @param fetchedAt işçinin değeri çektiği zaman
 */
record MarketQuoteResponse(
        String code,
        BigDecimal price,
        BigDecimal changePercent,
        String currency,
        Instant marketTime,
        Instant fetchedAt) {}
