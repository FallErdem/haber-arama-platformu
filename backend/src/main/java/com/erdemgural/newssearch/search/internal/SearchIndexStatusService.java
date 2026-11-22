package com.erdemgural.newssearch.search.internal;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch._types.ElasticsearchException;
import co.elastic.clients.elasticsearch._types.HealthStatus;
import com.erdemgural.newssearch.search.SearchIndexStatus;
import java.io.IOException;
import java.util.Set;
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

    private final OutboxRepository outbox;
    private final ElasticsearchClient client;

    SearchIndexStatusService(OutboxRepository outbox, ElasticsearchClient client) {
        this.outbox = outbox;
        this.client = client;
    }

    @Override
    public long pendingOutboxEvents() {
        return outbox.countPending();
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
