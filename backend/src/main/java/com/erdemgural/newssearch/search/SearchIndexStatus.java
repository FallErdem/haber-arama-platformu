package com.erdemgural.newssearch.search;

/** Arama indeksinin durumu; yönetim panosu için (FG-YP-12; API sözleşmesi 6.7). */
public interface SearchIndexStatus {

    /**
     * Elasticsearch'e henüz aktarılmamış değişiklik (outbox notu) sayısı. Sürekli artması aktarımda bir sorun
     * olduğunu gösterir.
     */
    long pendingOutboxEvents();

    /** Elasticsearch yanıt veriyor ve kümenin durumu kırmızı değilse {@code true}. */
    boolean isAvailable();
}
