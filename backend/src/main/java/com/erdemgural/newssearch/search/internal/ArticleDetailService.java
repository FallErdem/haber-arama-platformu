package com.erdemgural.newssearch.search.internal;

import com.erdemgural.newssearch.ingestion.ArticleCatalog;
import com.erdemgural.newssearch.ingestion.ArticleDetails;
import com.erdemgural.newssearch.ingestion.CategoryCatalog;
import com.erdemgural.newssearch.ingestion.CategoryWindows;
import com.erdemgural.newssearch.library.SavedArticles;
import com.erdemgural.newssearch.web.ApiException;
import com.erdemgural.newssearch.web.ErrorCode;
import java.time.Clock;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

/**
 * Haber detayı iki depodan birleştirilir (ADR-0019): meta veri, kaynak ve görseller PostgreSQL'den
 * ({@code ingestion} modülünün {@link ArticleCatalog} arayüzüyle), özet, tam metin ve yazar
 * Elasticsearch'ten. Detay bu yüzden {@code search} modülündedir: API'de Elasticsearch'e yalnızca bu
 * modül erişir ve modüllerin yönü {@code search → ingestion}'dır. Haberin kullanıcı tarafından
 * kaydedilip kaydedilmediği {@code library} modülünden ({@link SavedArticles}) sorulur.
 */
@Service
class ArticleDetailService {

    private final ArticleCatalog articleCatalog;
    private final ArticleSearchIndex searchIndex;
    private final CategoryCatalog categoryCatalog;
    private final SavedArticles savedArticles;
    private final Clock clock;

    ArticleDetailService(
            ArticleCatalog articleCatalog,
            ArticleSearchIndex searchIndex,
            CategoryCatalog categoryCatalog,
            SavedArticles savedArticles,
            Clock clock) {
        this.articleCatalog = articleCatalog;
        this.searchIndex = searchIndex;
        this.categoryCatalog = categoryCatalog;
        this.savedArticles = savedArticles;
        this.clock = clock;
    }

    /**
     * Haber detayı; {@code saved} alanı isteği yapan kullanıcıya göredir. Haber yoksa veya gizlenmişse
     * {@code 404 NOT_FOUND} (FG-AR-09), Elasticsearch'e ulaşılamazsa {@code 503 SEARCH_UNAVAILABLE}
     * fırlatır: metni olmayan bir detay sayfası kullanıcıya bozuk görünür.
     */
    ArticleDetailResponse find(UUID articleId, UUID userId) {
        ArticleDetails article = articleCatalog
                .findDetails(articleId)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, ErrorCode.NOT_FOUND));
        // Belge henüz aktarılmamışsa (outbox notu birkaç saniye içinde işlenir) metinler boş döner.
        IndexedTexts texts = searchIndex.findTexts(articleId).orElse(IndexedTexts.NONE);
        return new ArticleDetailResponse(
                article.id(),
                article.title(),
                texts.summary(),
                texts.content(),
                texts.author(),
                article.url(),
                new ArticleDetailResponse.Source(
                        article.sourceCode(),
                        article.sourceName(),
                        article.sourceHomepageUrl(),
                        article.sourceAttributionText()),
                article.language(),
                article.itemType(),
                CategoryWindows.current(
                        article.categories(), article.publishedAt(), categoryCatalog.timeWindows(), clock.instant()),
                article.publishedAt(),
                article.media().stream()
                        .map(media -> new ArticleDetailResponse.Media(
                                media.url(), media.width(), media.height(), media.caption(), media.credit()))
                        .toList(),
                List.of(),
                savedArticles.isSaved(userId, articleId));
    }
}
