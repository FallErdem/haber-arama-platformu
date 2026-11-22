package com.erdemgural.newssearch.ingestion.internal;

import com.erdemgural.newssearch.ingestion.ArticleAdministration;
import com.erdemgural.newssearch.ingestion.ArticleFilter;
import com.erdemgural.newssearch.ingestion.ManagedArticle;
import com.erdemgural.newssearch.web.ApiException;
import com.erdemgural.newssearch.web.ErrorCode;
import com.erdemgural.newssearch.web.PageParameters;
import com.erdemgural.newssearch.web.PageResponse;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

/**
 * {@link ArticleAdministration}'ın uygulaması. Gizleme ve geri alma kendi işlemini açmaz; çağıranın işleminde
 * çalışır (outbox notu ve audit kaydı aynı işlemde yazılsın diye).
 */
@Service
class ArticleAdministrationService implements ArticleAdministration {

    private final ManagedArticleRepository repository;

    ArticleAdministrationService(ManagedArticleRepository repository) {
        this.repository = repository;
    }

    @Override
    public PageResponse<ManagedArticle> list(ArticleFilter filter, PageParameters page) {
        return PageResponse.of(repository.findPage(filter, page.size(), page.offset()), page, repository.count(filter));
    }

    @Override
    public ManagedArticle hide(UUID articleId, UUID adminId, String reason) {
        boolean hidden = repository.findHiddenForUpdate(articleId).orElseThrow(ArticleAdministrationService::notFound);
        if (hidden) {
            throw new ApiException(HttpStatus.CONFLICT, ErrorCode.INVALID_STATE_TRANSITION);
        }
        repository.hide(articleId, adminId, reason);
        return repository.findById(articleId).orElseThrow(ArticleAdministrationService::notFound);
    }

    @Override
    public ManagedArticle unhide(UUID articleId) {
        boolean hidden = repository.findHiddenForUpdate(articleId).orElseThrow(ArticleAdministrationService::notFound);
        if (!hidden) {
            throw new ApiException(HttpStatus.CONFLICT, ErrorCode.INVALID_STATE_TRANSITION);
        }
        repository.unhide(articleId);
        return repository.findById(articleId).orElseThrow(ArticleAdministrationService::notFound);
    }

    private static ApiException notFound() {
        return new ApiException(HttpStatus.NOT_FOUND, ErrorCode.NOT_FOUND);
    }
}
