package com.erdemgural.newssearch.search.internal;

import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/**
 * {@code outbox_events} tablosu (veri modeli 3.10; bu modülün tablosu). Notları işçi Elasticsearch'e aktarır;
 * API yalnızca not ekler ve bekleyenleri sayar.
 */
@Repository
class OutboxRepository {

    private final JdbcClient jdbcClient;

    OutboxRepository(JdbcClient jdbcClient) {
        this.jdbcClient = jdbcClient;
    }

    /** Bekleyen notlar ({@code outbox_events_pending_next_attempt_at_idx} kısmi indeksinden sayılır). */
    long countPending() {
        return jdbcClient
                .sql("SELECT count(*) FROM outbox_events WHERE status = 'PENDING'")
                .query(Long.class)
                .single();
    }

    /**
     * "Bu haberin arama belgesini güncelle" notu. Metin taşımaz: işçi belgede yalnızca meta veriyi (gizleme
     * dahil) haberin PostgreSQL'deki güncel hâlinden yazar (ADR-0012, ADR-0019).
     */
    void insertIndexNote(UUID articleId) {
        jdbcClient.sql("""
				INSERT INTO outbox_events (article_id, operation, status, next_attempt_at)
				VALUES (:articleId, 'INDEX', 'PENDING', now())
				""").param("articleId", articleId).update();
    }
}
