package com.erdemgural.newssearch.ingestion.internal;

import com.erdemgural.newssearch.ingestion.CategoryWindows;
import com.erdemgural.newssearch.web.ApiException;
import com.erdemgural.newssearch.web.ErrorCode;
import java.time.Clock;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

@Service
class ArticleDetailService {

    private final ArticleRepository articleRepository;
    private final MediaRepository mediaRepository;
    private final CategoryRepository categoryRepository;
    private final MediaUrlSigner signer;
    private final Clock clock;

    ArticleDetailService(
            ArticleRepository articleRepository,
            MediaRepository mediaRepository,
            CategoryRepository categoryRepository,
            MediaUrlSigner signer,
            Clock clock) {
        this.articleRepository = articleRepository;
        this.mediaRepository = mediaRepository;
        this.categoryRepository = categoryRepository;
        this.signer = signer;
        this.clock = clock;
    }

    /** Haber detayı. Haber yoksa veya gizlenmişse {@code 404 NOT_FOUND} fırlatır (FG-AR-09). */
    ArticleDetailResponse find(UUID articleId) {
        ArticleRepository.ArticleDetailRow article = articleRepository
                .findDetail(articleId)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, ErrorCode.NOT_FOUND));
        List<ArticleDetailResponse.Media> media = mediaRepository.findDownloadedByArticle(articleId).stream()
                .map(item -> new ArticleDetailResponse.Media(
                        signer.signedUrl(item.id()), item.width(), item.height(), item.caption(), item.credit()))
                .toList();
        return new ArticleDetailResponse(
                article.id(),
                article.title(),
                article.summary(),
                article.content(),
                article.author(),
                article.url(),
                new ArticleDetailResponse.Source(
                        article.sourceCode(),
                        article.sourceName(),
                        article.sourceHomepageUrl(),
                        article.sourceAttributionText()),
                article.language(),
                article.itemType(),
                CategoryWindows.current(
                        article.categories(), article.publishedAt(), categoryRepository.timeWindows(), clock.instant()),
                article.publishedAt(),
                media,
                List.of(),
                false);
    }
}
