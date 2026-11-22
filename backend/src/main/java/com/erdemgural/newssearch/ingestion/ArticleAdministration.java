package com.erdemgural.newssearch.ingestion;

import com.erdemgural.newssearch.web.PageParameters;
import com.erdemgural.newssearch.web.PageResponse;
import java.util.UUID;

/**
 * Yönetim panelinde haberler: liste ve gizleme durumu (FG-YP-09; API sözleşmesi 6.6). Haber tablosu bu
 * modüldedir.
 *
 * <p>Gizleme ve geri alma çağıranın veritabanı işleminde çalışır: arama indeksinin güncellenmesi için outbox
 * notunu ve audit kaydını çağıran ({@code search} modülü) aynı işlemde yazar. Haber yoksa
 * {@code 404 NOT_FOUND}; zaten gizli haberi gizleme veya gizli olmayanı geri alma
 * {@code 409 INVALID_STATE_TRANSITION}.
 */
public interface ArticleAdministration {

    /** Gizli haberler en son gizlenen önce; diğerleri en yeni yayımlanan önce. */
    PageResponse<ManagedArticle> list(ArticleFilter filter, PageParameters page);

    ManagedArticle hide(UUID articleId, UUID adminId, String reason);

    ManagedArticle unhide(UUID articleId);
}
