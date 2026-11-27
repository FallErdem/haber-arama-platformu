package com.erdemgural.newssearch.market.internal;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** {@code market_quotes} tablosu (V23). API yalnızca okur; satırları işçi yazar. */
@Repository
class MarketQuoteRepository {

    /** Tablodaki bir satır. */
    record MarketQuoteRow(
            String code,
            BigDecimal price,
            BigDecimal previousClose,
            String currency,
            Instant marketTime,
            Instant fetchedAt) {}

    private final JdbcClient jdbcClient;

    MarketQuoteRepository(JdbcClient jdbcClient) {
        this.jdbcClient = jdbcClient;
    }

    /** Bütün değerler. Tabloda en fazla altı satır vardır; ekrandaki sırayı arayüz belirler. */
    List<MarketQuoteRow> findAll() {
        return jdbcClient
                .sql("""
				SELECT code, price, previous_close, currency, market_time, fetched_at
				FROM market_quotes
				ORDER BY code
				""")
                .query((row, rowNumber) -> new MarketQuoteRow(
                        row.getString("code"),
                        row.getBigDecimal("price"),
                        row.getBigDecimal("previous_close"),
                        row.getString("currency"),
                        row.getTimestamp("market_time").toInstant(),
                        row.getTimestamp("fetched_at").toInstant()))
                .list();
    }
}
