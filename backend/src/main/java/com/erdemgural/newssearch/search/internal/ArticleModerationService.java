package com.erdemgural.newssearch.search.internal;

import com.erdemgural.newssearch.audit.AuditAction;
import com.erdemgural.newssearch.audit.AuditEvent;
import com.erdemgural.newssearch.audit.AuditLog;
import com.erdemgural.newssearch.audit.AuditTargetType;
import com.erdemgural.newssearch.ingestion.ArticleAdministration;
import com.erdemgural.newssearch.ingestion.ManagedArticle;
import com.erdemgural.newssearch.search.ArticleModeration;
import com.erdemgural.newssearch.web.ApiException;
import java.util.Map;
import java.util.UUID;
import java.util.function.Supplier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * {@link ArticleModeration}'ın uygulaması. Haberin satırı, outbox notu ve audit kaydı tek işlemde yazılır. Kural
 * ihlalinde (409) işlem geri alınır; denemenin {@code FAILURE} kaydı işlem bittikten sonra ayrıca yazılır
 * (diğer yönetim işlemleriyle aynı kural). Bu yüzden işlem {@link TransactionTemplate} ile açılır.
 */
@Service
class ArticleModerationService implements ArticleModeration {

    private static final Logger log = LoggerFactory.getLogger(ArticleModerationService.class);

    private final ArticleAdministration articles;
    private final OutboxRepository outbox;
    private final AuditLog auditLog;
    private final TransactionTemplate transactionTemplate;

    ArticleModerationService(
            ArticleAdministration articles,
            OutboxRepository outbox,
            AuditLog auditLog,
            TransactionTemplate transactionTemplate) {
        this.articles = articles;
        this.outbox = outbox;
        this.auditLog = auditLog;
        this.transactionTemplate = transactionTemplate;
    }

    @Override
    public ManagedArticle hide(UUID adminId, UUID articleId, String reason) {
        return audited(adminId, AuditAction.ARTICLE_HIDDEN, articleId, () -> {
            ManagedArticle article = articles.hide(articleId, adminId, reason);
            outbox.insertIndexNote(articleId);
            auditLog.record(AuditEvent.success(
                    adminId, AuditAction.ARTICLE_HIDDEN, AuditTargetType.ARTICLE, articleId, Map.of("reason", reason)));
            return article;
        });
    }

    @Override
    public ManagedArticle unhide(UUID adminId, UUID articleId) {
        return audited(adminId, AuditAction.ARTICLE_UNHIDDEN, articleId, () -> {
            ManagedArticle article = articles.unhide(articleId);
            outbox.insertIndexNote(articleId);
            auditLog.record(AuditEvent.success(
                    adminId, AuditAction.ARTICLE_UNHIDDEN, AuditTargetType.ARTICLE, articleId, Map.of()));
            return article;
        });
    }

    /**
     * İşi bir veritabanı işleminde çalıştırır. Kural ihlalinde (409) işlem geri alınmıştır; deneme işlemin
     * dışında {@code FAILURE} olarak yazılır ve hata yine istemciye döner. Haberin bulunamaması (404) deneme
     * sayılmaz.
     */
    private ManagedArticle audited(UUID adminId, AuditAction action, UUID articleId, Supplier<ManagedArticle> work) {
        try {
            return transactionTemplate.execute(transaction -> work.get());
        } catch (ApiException exception) {
            if (exception.status() == HttpStatus.CONFLICT) {
                recordFailure(adminId, action, articleId, exception);
            }
            throw exception;
        }
    }

    private void recordFailure(UUID adminId, AuditAction action, UUID articleId, ApiException exception) {
        try {
            auditLog.record(AuditEvent.failure(
                    adminId,
                    action,
                    AuditTargetType.ARTICLE,
                    articleId,
                    Map.of("code", exception.code().name())));
        } catch (DataAccessException failure) {
            log.error("Reddedilen haber gizleme işleminin audit kaydı yazılamadı", failure);
        }
    }
}
