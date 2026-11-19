package com.erdemgural.newssearch.library;

import java.util.Collection;
import java.util.Set;
import java.util.UUID;

/**
 * Kaydedilen haberlere diğer modüllerin erişim yolu. Arama sonuçları ve haber detayı (arama modülü),
 * haberlerin kullanıcı tarafından kaydedilip kaydedilmediğini buradan sorar (API sözleşmesi 4.1 ve
 * 4.2, {@code saved} alanı).
 */
public interface SavedArticles {

    boolean isSaved(UUID userId, UUID articleId);

    /** Verilen haberlerden kullanıcının kaydettikleri; bir arama sayfası için tek sorgu. */
    Set<UUID> findSaved(UUID userId, Collection<UUID> articleIds);
}
