package com.erdemgural.newssearch.market.internal;

import com.erdemgural.newssearch.market.internal.MarketQuoteRepository.MarketQuoteRow;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;
import org.springframework.stereotype.Service;

@Service
class MarketQuoteService {

    private static final BigDecimal HUNDRED = BigDecimal.valueOf(100);

    private final MarketQuoteRepository repository;

    MarketQuoteService(MarketQuoteRepository repository) {
        this.repository = repository;
    }

    /** Bütün değerler, değişim yüzdesiyle birlikte. İşçi henüz hiç çekmediyse liste boştur. */
    List<MarketQuoteResponse> findAll() {
        return repository.findAll().stream()
                .map(row -> new MarketQuoteResponse(
                        row.code(), row.price(), changePercent(row), row.currency(), row.marketTime(), row.fetchedAt()))
                .toList();
    }

    /**
     * Önceki kapanışa göre değişim: (fiyat − önceki kapanış) × 100 ÷ önceki kapanış, iki basamağa yuvarlanır.
     * Önceki kapanış her zaman sıfırdan büyüktür (V23'teki kural); bölme hata vermez.
     */
    private static BigDecimal changePercent(MarketQuoteRow row) {
        return row.price()
                .subtract(row.previousClose())
                .multiply(HUNDRED)
                .divide(row.previousClose(), 2, RoundingMode.HALF_UP);
    }
}
