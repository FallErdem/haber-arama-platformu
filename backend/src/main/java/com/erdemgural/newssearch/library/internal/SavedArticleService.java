package com.erdemgural.newssearch.library.internal;

import com.erdemgural.newssearch.ingestion.ArticleCatalog;
import com.erdemgural.newssearch.ingestion.ArticleImage;
import com.erdemgural.newssearch.ingestion.ArticleSummary;
import com.erdemgural.newssearch.library.SavedArticles;
import com.erdemgural.newssearch.library.internal.SavedArticleRepository.SavedArticleRow;
import com.erdemgural.newssearch.web.ApiException;
import com.erdemgural.newssearch.web.ErrorCode;
import com.erdemgural.newssearch.web.PageParameters;
import com.erdemgural.newssearch.web.PageResponse;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

/**
 * Kaydedilen haberler (FG-KO-01 – 03). Kayıtlar bu modülün tablosundadır; haberin başlığı, kaynağı ve
 * görseli {@code ingestion} modülünden {@link ArticleCatalog} ile alınır.
 */
@Service
class SavedArticleService implements SavedArticles {

    private final SavedArticleRepository repository;
    private final ArticleCatalog articleCatalog;

    SavedArticleService(SavedArticleRepository repository, ArticleCatalog articleCatalog) {
        this.repository = repository;
        this.articleCatalog = articleCatalog;
    }

    /** Haberi kaydeder. Haber yoksa veya gizlenmişse {@code 404 NOT_FOUND}: kullanıcı onu göremez. */
    void save(UUID userId, UUID articleId) {
        if (!articleCatalog.findSummaries(List.of(articleId)).containsKey(articleId)) {
            throw new ApiException(HttpStatus.NOT_FOUND, ErrorCode.NOT_FOUND);
        }
        repository.save(userId, articleId);
    }

    void remove(UUID userId, UUID articleId) {
        repository.delete(userId, articleId);
    }

    /**
     * Kullanıcının kaydettiği haberlerden bir sayfa, kaydedilme zamanına göre yeniden eskiye (FG-KO-02).
     * {@link ArticleCatalog#findSummaries} gizlenmiş haberi döndürmez; karşılığı gelmeyen kayıt gizlenmiş
     * bir haberdir (FG-KO-03). Haberler silinmez; kaynak içeriği silindiğinde kayıtlar da
     * {@code ON DELETE CASCADE} ile silinir.
     */
    PageResponse<SavedArticleItem> list(UUID userId, PageParameters page) {
        List<SavedArticleRow> rows = repository.findPage(userId, page.size(), page.offset());
        Map<UUID, ArticleSummary> summaries = articleCatalog.findSummaries(
                rows.stream().map(SavedArticleRow::articleId).toList());
        List<SavedArticleItem> items = rows.stream()
                .map(row -> toItem(row, summaries.get(row.articleId())))
                .toList();
        return PageResponse.of(items, page, repository.count(userId));
    }

    @Override
    public boolean isSaved(UUID userId, UUID articleId) {
        return repository.exists(userId, articleId);
    }

    @Override
    public Set<UUID> findSaved(UUID userId, Collection<UUID> articleIds) {
        return repository.findSavedAmong(userId, articleIds);
    }

    private static SavedArticleItem toItem(SavedArticleRow row, ArticleSummary summary) {
        if (summary == null) {
            return new SavedArticleItem(row.articleId(), row.savedAt(), true, null);
        }
        ArticleImage mainImage = summary.image();
        SavedArticleItem.Image image = mainImage == null
                ? null
                : new SavedArticleItem.Image(mainImage.url(), mainImage.width(), mainImage.height());
        return new SavedArticleItem(
                row.articleId(),
                row.savedAt(),
                false,
                new SavedArticleItem.Article(
                        summary.title(),
                        new SavedArticleItem.Source(summary.sourceCode(), summary.sourceName()),
                        summary.publishedAt(),
                        image));
    }
}
