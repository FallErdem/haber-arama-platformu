package com.erdemgural.newssearch.admin.internal;

import com.erdemgural.newssearch.ingestion.ManagedArticle;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;

/**
 * Yönetim panelindeki bir haber (API sözleşmesi 6.6).
 *
 * @param hiddenByEmail gizleyen yöneticinin e-postası; gizli değilse {@code null}
 */
record AdminArticleResponse(
        UUID id,
        String title,
        String url,
        String sourceCode,
        String sourceName,
        Instant publishedAt,
        boolean hidden,
        Instant hiddenAt,
        String hiddenReason,
        UUID hiddenBy,
        String hiddenByEmail) {

    /** @param emails kullanıcı kimliğinden e-postaya */
    static AdminArticleResponse from(ManagedArticle article, Map<UUID, String> emails) {
        return new AdminArticleResponse(
                article.id(),
                article.title(),
                article.url(),
                article.sourceCode(),
                article.sourceName(),
                article.publishedAt(),
                article.hidden(),
                article.hiddenAt(),
                article.hiddenReason(),
                article.hiddenBy(),
                article.hiddenBy() == null ? null : emails.get(article.hiddenBy()));
    }
}
