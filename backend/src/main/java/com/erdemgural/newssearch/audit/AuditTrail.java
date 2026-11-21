package com.erdemgural.newssearch.audit;

import com.erdemgural.newssearch.web.PageParameters;
import com.erdemgural.newssearch.web.PageResponse;
import java.util.List;
import java.util.function.Consumer;

/**
 * Audit kayıtlarının okunması: yönetim panelindeki liste ve CSV dışa aktarma (FG-YP-10, FG-YP-11). Yazma
 * yolu {@link AuditLog}'dur; burada yalnızca okuma vardır.
 */
public interface AuditTrail {

    /** Kayıtlar, zamana göre yeniden eskiye. */
    PageResponse<AuditRecord> list(AuditEventFilter filter, PageParameters page);

    /** Filtreye uyan kayıt sayısı (dışa aktarma sınırı için). */
    long count(AuditEventFilter filter);

    /**
     * Filtreye uyan bütün kayıtları, yeniden eskiye, parça parça verir. Kayıtlar belleğe birden alınmaz;
     * her parça işlendikten sonra sıradaki okunur.
     */
    void forEachChunk(AuditEventFilter filter, Consumer<List<AuditRecord>> consumer);
}
