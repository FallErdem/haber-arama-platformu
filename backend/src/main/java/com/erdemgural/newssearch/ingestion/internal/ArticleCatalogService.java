package com.erdemgural.newssearch.ingestion.internal;

import com.erdemgural.newssearch.ingestion.ArticleCatalog;
import com.erdemgural.newssearch.ingestion.ArticleDetails;
import com.erdemgural.newssearch.ingestion.ArticleImage;
import com.erdemgural.newssearch.ingestion.ArticleSummary;
import java.util.Collection;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;

/** {@link ArticleCatalog}'un uygulaması: haber meta verisi ve imzalı görsel adresleri. */
@Service
class ArticleCatalogService implements ArticleCatalog {

    private final ArticleRepository articleRepository;
    private final MediaRepository mediaRepository;
    private final MediaUrlSigner signer;

    ArticleCatalogService(ArticleRepository articleRepository, MediaRepository mediaRepository, MediaUrlSigner signer) {
        this.articleRepository = articleRepository;
        this.mediaRepository = mediaRepository;
        this.signer = signer;
    }

    @Override
    public Map<UUID, ArticleSummary> findSummaries(Collection<UUID> articleIds) {
        Map<UUID, ArticleSummary> summaries = articleRepository.findSummaries(articleIds);
        Map<UUID, MediaRepository.DownloadedMedia> mainImages = mediaRepository.findMainImages(summaries.keySet());
        return summaries.values().stream()
                .map(summary -> {
                    MediaRepository.DownloadedMedia image = mainImages.get(summary.id());
                    return image == null ? summary : summary.withImage(toImage(image));
                })
                .collect(Collectors.toMap(ArticleSummary::id, summary -> summary));
    }

    @Override
    public Optional<ArticleDetails> findDetails(UUID articleId) {
        return articleRepository
                .findDetail(articleId)
                .map(article -> new ArticleDetails(
                        article.id(),
                        article.title(),
                        article.url(),
                        article.sourceCode(),
                        article.sourceName(),
                        article.sourceHomepageUrl(),
                        article.sourceAttributionText(),
                        article.language(),
                        article.itemType(),
                        article.categories(),
                        article.publishedAt(),
                        mediaRepository.findDownloadedByArticle(articleId).stream()
                                .map(media -> new ArticleDetails.ArticleMedia(
                                        signer.signedUrl(media.id()),
                                        media.width(),
                                        media.height(),
                                        media.caption(),
                                        media.credit()))
                                .toList()));
    }

    private ArticleImage toImage(MediaRepository.DownloadedMedia media) {
        return new ArticleImage(signer.signedUrl(media.id()), media.width(), media.height());
    }
}
