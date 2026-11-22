package com.erdemgural.newssearch.search.internal;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch._types.ElasticsearchException;
import co.elastic.clients.elasticsearch._types.HealthStatus;
import com.erdemgural.newssearch.search.SearchIndexStatus;
import java.io.IOException;
import java.util.Set;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;

/**
 * {@link SearchIndexStatus}'un uygulaması. Bekleyen notlar PostgreSQL'den ({@code outbox_events}, bu modülün
 * tablosu), kümenin durumu Elasticsearch'ten okunur. {@code news_api} kullanıcısının kümenin durumunu okuma
 * ({@code monitor}) yetkisi vardır.
 */
@Service
class SearchIndexStatusService implements SearchIndexStatus {

    /**
     * Arama yapılabilen durumlar: yeşil ve sarı. Kırmızıda bazı haberler aranamaz. (Sarı: bütün veri okunabilir,
     * yalnızca başka bir sunucudaki yedek kopyası eksik.)
     */
    private static final Set<HealthStatus> SERVING = Set.of(HealthStatus.Green, HealthStatus.Yellow);

    private final JdbcClient jdbcClient;
    private final ElasticsearchClient client;

    SearchIndexStatusService(JdbcClient jdbcClient, ElasticsearchClient client) {
        this.jdbcClient = jdbcClient;
        this.client = client;
    }

    /** Bekleyen notlar ({@code outbox_events_pending_next_attempt_at_idx} kısmi indeksinden sayılır). */
    @Override
    public long pendingOutboxEvents() {
        return jdbcClient
                .sql("SELECT count(*) FROM outbox_events WHERE status = 'PENDING'")
                .query(Long.class)
                .single();
    }

    /** Elasticsearch'e ulaşılamazsa bağlantı ayarındaki süre (2 sn) dolunca {@code false} döner. */
    @Override
    public boolean isAvailable() {
        try {
            return SERVING.contains(client.cluster().health().status());
        } catch (IOException | ElasticsearchException exception) {
            return false;
        }
    }
}
