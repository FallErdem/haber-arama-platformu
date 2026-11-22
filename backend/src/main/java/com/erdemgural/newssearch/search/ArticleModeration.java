package com.erdemgural.newssearch.search;

import com.erdemgural.newssearch.ingestion.ManagedArticle;
import java.util.UUID;

/**
 * Haber gizleme ve gizlemeyi geri alma (FG-YP-09, FG-AR-09; API sözleşmesi 6.6).
 *
 * <p>Bu işlem iki modülün tablosuna yazar: haberin satırı ({@code ingestion}) ve arama indeksini güncelleyecek
 * outbox notu (bu modül). İkisi ve audit kaydı tek veritabanı işleminde yazılır. İşi bu modül yönetir; çünkü bu
 * modül zaten {@code ingestion}'ı kullanıyor, tersi iki modülü birbirine bağlardı.
 *
 * <p>Haber yoksa {@code 404 NOT_FOUND}; zaten gizli haberi gizleme veya gizli olmayanı geri alma
 * {@code 409 INVALID_STATE_TRANSITION}. Başarılı işlem de reddedilen deneme de audit log'a yazılır.
 */
public interface ArticleModeration {

    ManagedArticle hide(UUID adminId, UUID articleId, String reason);

    ManagedArticle unhide(UUID adminId, UUID articleId);
}
