package com.erdemgural.newssearch.search.internal;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch._types.ElasticsearchException;
import co.elastic.clients.elasticsearch.core.SearchResponse;
import co.elastic.clients.elasticsearch.core.search.TotalHits;
import co.elastic.clients.elasticsearch.core.search.TotalHitsRelation;
import com.erdemgural.newssearch.web.ApiException;
import com.erdemgural.newssearch.web.ErrorCode;
import java.io.IOException;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;

/** Arama indeksine (Elasticsearch) erişim. Uygulama indeksi yalnızca okur. */
@Component
class ArticleSearchIndex {

    private final ElasticsearchClient client;

    ArticleSearchIndex(ElasticsearchClient client) {
        this.client = client;
    }

    /**
     * Aramayı çalıştırır. Elasticsearch'e ulaşılamazsa veya hata dönerse {@code 503
     * SEARCH_UNAVAILABLE} fırlatır: arama o an kullanılamaz, uygulamanın geri kalanı çalışır
     * (FOG-09).
     */
    SearchHits search(SearchCriteria criteria, Map<String, Duration> categoryWindows) {
        SearchResponse<IndexedTexts> response;
        try {
            response = client.search(ArticleSearchQuery.build(criteria, categoryWindows), IndexedTexts.class);
        } catch (IOException | ElasticsearchException exception) {
            throw unavailable(exception);
        }

        // Belge kimliği haberin kimliğidir (işçi böyle yazar). Özetin tek kaydı belgedir (ADR-0019).
        List<SearchHits.Hit> hits = response.hits().hits().stream()
                .map(hit -> new SearchHits.Hit(
                        UUID.fromString(hit.id()),
                        hit.source() == null ? null : hit.source().summary(),
                        hit.highlight()))
                .toList();
        TotalHits total = response.hits().total();
        if (total == null) {
            return new SearchHits(hits, hits.size(), true);
        }
        return new SearchHits(hits, total.value(), total.relation() == TotalHitsRelation.Eq);
    }

    /**
     * Bir haberin metinleri (özet, tam metin, yazar). Belge yoksa boş döner. Elasticsearch'e
     * ulaşılamazsa {@code 503 SEARCH_UNAVAILABLE} fırlatır.
     *
     * <p>Belgenin hangi aylık indekste olduğu bilinmediğinden takma ad üzerinde kimliğiyle aranır;
     * Elasticsearch, birden fazla indeksi kapsayan bir takma adda kimlikle doğrudan okumaya izin vermez.
     */
    Optional<IndexedTexts> findTexts(UUID articleId) {
        SearchResponse<IndexedTexts> response;
        try {
            response = client.search(ArticleSearchQuery.texts(articleId), IndexedTexts.class);
        } catch (IOException | ElasticsearchException exception) {
            throw unavailable(exception);
        }
        return response.hits().hits().stream().findFirst().map(hit -> hit.source());
    }

    private static ApiException unavailable(Exception cause) {
        return new ApiException(HttpStatus.SERVICE_UNAVAILABLE, ErrorCode.SEARCH_UNAVAILABLE, cause);
    }
}
