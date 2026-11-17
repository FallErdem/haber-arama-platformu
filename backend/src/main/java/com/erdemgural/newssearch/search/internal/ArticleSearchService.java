package com.erdemgural.newssearch.search.internal;

import com.erdemgural.newssearch.ingestion.ArticleCatalog;
import com.erdemgural.newssearch.ingestion.ArticleSummary;
import com.erdemgural.newssearch.ingestion.CategoryCatalog;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import org.springframework.stereotype.Service;

/**
 * Arama akışı: eşleşen haberlerin kimlikleri ve sırası Elasticsearch'ten, gösterilecek bilgileri
 * PostgreSQL'den gelir (veri modeli 5.2). Arama indeksi türetilmiş bir kopyadır; başlık, kaynak adı
 * veya adres gibi bilgilerin tek doğru kaynağı asıl kayıttır.
 */
@Service
class ArticleSearchService {

    private final ArticleSearchIndex searchIndex;
    private final ArticleCatalog articleCatalog;
    private final CategoryCatalog categoryCatalog;
    private final Clock clock;

    ArticleSearchService(
            ArticleSearchIndex searchIndex,
            ArticleCatalog articleCatalog,
            CategoryCatalog categoryCatalog,
            Clock clock) {
        this.searchIndex = searchIndex;
        this.articleCatalog = articleCatalog;
        this.categoryCatalog = categoryCatalog;
        this.clock = clock;
    }

    ArticleSearchResponse search(SearchCriteria criteria) {
        Map<String, Duration> categoryWindows = categoryCatalog.timeWindows();
        SearchHits hits = searchIndex.search(criteria, categoryWindows);

        List<UUID> articleIds =
                hits.hits().stream().map(SearchHits.Hit::articleId).toList();
        Map<UUID, ArticleSummary> summaries = articleCatalog.findSummaries(articleIds);
        Instant now = clock.instant();

        // Sıra Elasticsearch'in verdiği sıradır. İndekste olup asıl kayıtta bulunmayan veya gizlenmiş
        // bir haber (outbox notu henüz işlenmemiş olabilir) sonuçta gösterilmez (FG-AR-09).
        List<ArticleSearchItem> items = hits.hits().stream()
                .map(hit -> {
                    ArticleSummary summary = summaries.get(hit.articleId());
                    return summary == null ? null : toItem(summary, hit, criteria, categoryWindows, now);
                })
                .filter(Objects::nonNull)
                .toList();

        int totalPages = (int) Math.ceil((double) hits.total() / criteria.size());
        return new ArticleSearchResponse(
                items, criteria.page(), criteria.size(), hits.total(), totalPages, hits.totalIsExact() ? "eq" : "gte");
    }

    private static ArticleSearchItem toItem(
            ArticleSummary summary,
            SearchHits.Hit hit,
            SearchCriteria criteria,
            Map<String, Duration> categoryWindows,
            Instant now) {
        return new ArticleSearchItem(
                summary.id(),
                summary.title(),
                criteria.hasQuery() ? highlights(hit.highlights(), summary.language()) : null,
                summary.summary(),
                new ArticleSearchItem.Source(summary.sourceCode(), summary.sourceName()),
                summary.language(),
                summary.itemType(),
                currentCategories(summary, categoryWindows, now),
                summary.publishedAt(),
                summary.url(),
                null,
                0);
    }

    /**
     * Süreli bir kategori (Son Dakika), süresi dolmuş haberde gösterilmez (FG-AR-12); haber konu
     * kategorileriyle görünmeye devam eder.
     */
    private static List<String> currentCategories(
            ArticleSummary summary, Map<String, Duration> categoryWindows, Instant now) {
        return summary.categories().stream()
                .filter(code -> {
                    Duration window = categoryWindows.get(code);
                    return window == null || summary.publishedAt().isAfter(now.minus(window));
                })
                .toList();
    }

    /**
     * Elasticsearch vurguları alan adıyla verir ({@code title_tr}); yanıtta dilden bağımsız
     * {@code title} ve {@code summary} anahtarları kullanılır. Asıl alanın vurgusu yoksa (eşleşme
     * yalnızca katlanmış alt alandaysa) alt alanın vurgusu alınır.
     */
    private static Map<String, List<String>> highlights(Map<String, List<String>> byField, String language) {
        Map<String, List<String>> highlights = new LinkedHashMap<>();
        for (String name : List.of("title", "summary")) {
            String field = name + "_" + language;
            List<String> fragments = byField.getOrDefault(field, byField.get(field + ".folded"));
            if (fragments != null) {
                highlights.put(name, fragments);
            }
        }
        return highlights;
    }
}
