package com.erdemgural.newssearch.library;

import java.util.UUID;

/**
 * Kaydedilen haberlere diğer modüllerin erişim yolu. Haber detayı (arama modülü), haberin kullanıcı
 * tarafından kaydedilip kaydedilmediğini buradan sorar (API sözleşmesi 4.2, {@code saved} alanı).
 */
public interface SavedArticles {

    boolean isSaved(UUID userId, UUID articleId);
}
