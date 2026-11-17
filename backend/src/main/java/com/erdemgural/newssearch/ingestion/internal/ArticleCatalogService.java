package com.erdemgural.newssearch.ingestion.internal;

import com.erdemgural.newssearch.ingestion.ArticleCatalog;
import com.erdemgural.newssearch.ingestion.ArticleImage;
import com.erdemgural.newssearch.ingestion.ArticleSummary;
import java.util.Collection;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;

/** {@link ArticleCatalog}'un uygulaması: haber özetleri ve imzalı ana görsel adresleri, iki sorguyla. */
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

    private ArticleImage toImage(MediaRepository.DownloadedMedia media) {
        return new ArticleImage(signer.signedUrl(media.id()), media.width(), media.height());
    }
}
