package com.erdemgural.newssearch.search.internal;

import com.erdemgural.newssearch.ingestion.ArticleCatalog;
import com.erdemgural.newssearch.ingestion.ArticleSummary;
import com.erdemgural.newssearch.ingestion.CategoryCatalog;
import com.erdemgural.newssearch.ingestion.CategoryWindows;
import com.erdemgural.newssearch.library.SavedArticles;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import org.springframework.stereotype.Service;

/**
 * Arama akışı: eşleşen haberlerin kimlikleri, sırası, özetleri ve vurguları Elasticsearch'ten, meta
 * verisi (başlık, kaynak adı, adres, kategoriler, görsel) PostgreSQL'den gelir (veri modeli 5.2;
 * ADR-0019). Hangi sonuçların kullanıcı tarafından kaydedildiği {@code library} modülünden sorulur.
 */
@Service
class ArticleSearchService {

    private final ArticleSearchIndex searchIndex;
    private final ArticleCatalog articleCatalog;
    private final CategoryCatalog categoryCatalog;
    private final SavedArticles savedArticles;
    private final Clock clock;

    ArticleSearchService(
            ArticleSearchIndex searchIndex,
            ArticleCatalog articleCatalog,
            CategoryCatalog categoryCatalog,
            SavedArticles savedArticles,
            Clock clock) {
        this.searchIndex = searchIndex;
        this.articleCatalog = articleCatalog;
        this.categoryCatalog = categoryCatalog;
        this.savedArticles = savedArticles;
        this.clock = clock;
    }

    /** {@code userId}: sonuçlardaki {@code saved} alanı isteği yapan kullanıcıya göredir. */
    ArticleSearchResponse search(SearchCriteria criteria, UUID userId) {
        Map<String, Duration> categoryWindows = categoryCatalog.timeWindows();
        SearchHits hits = searchIndex.search(criteria, categoryWindows);

        List<UUID> articleIds =
                hits.hits().stream().map(SearchHits.Hit::articleId).toList();
        Map<UUID, ArticleSummary> summaries = articleCatalog.findSummaries(articleIds);
        Set<UUID> saved = savedArticles.findSaved(userId, summaries.keySet());
        Instant now = clock.instant();

        // Sıra Elasticsearch'in verdiği sıradır. İndekste olup asıl kayıtta bulunmayan veya gizlenmiş
        // bir haber (outbox notu henüz işlenmemiş olabilir) sonuçta gösterilmez (FG-AR-09).
        List<ArticleSearchItem> items = hits.hits().stream()
                .map(hit -> {
                    ArticleSummary summary = summaries.get(hit.articleId());
                    return summary == null
                            ? null
                            : toItem(summary, hit, criteria, categoryWindows, now, saved.contains(summary.id()));
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
            Instant now,
            boolean saved) {
        return new ArticleSearchItem(
                summary.id(),
                summary.title(),
                criteria.hasQuery() ? highlights(hit.highlights(), summary.language()) : null,
                hit.summary(),
                new ArticleSearchItem.Source(summary.sourceCode(), summary.sourceName()),
                summary.language(),
                summary.itemType(),
                CategoryWindows.current(summary.categories(), summary.publishedAt(), categoryWindows, now),
                summary.publishedAt(),
                summary.url(),
                summary.image() == null
                        ? null
                        : new ArticleSearchItem.Image(
                                summary.image().url(),
                                summary.image().width(),
                                summary.image().height()),
                0,
                saved);
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
