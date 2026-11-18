package com.erdemgural.newssearch.search.internal;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Bir haberin Elasticsearch belgesindeki metinleri: özet, tam metin (HTML) ve yazar. Metinlerin tek
 * kaydı Elasticsearch'tir (ADR-0019). Belgede haberin diline göre yalnızca `_tr` ya da `_en` alanları
 * doludur.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
record IndexedTexts(
        @JsonProperty("summary_tr") String summaryTr,
        @JsonProperty("summary_en") String summaryEn,
        @JsonProperty("content_tr") String contentTr,
        @JsonProperty("content_en") String contentEn,
        @JsonProperty("author") String author) {

    /** Belgede metin bulunamadığında (belge henüz aktarılmamışsa) kullanılan boş metinler. */
    static final IndexedTexts NONE = new IndexedTexts(null, null, null, null, null);

    /** Belgenin dilindeki özet; yoksa {@code null}. */
    String summary() {
        return summaryTr != null ? summaryTr : summaryEn;
    }

    /** Belgenin dilindeki tam metin; yoksa {@code null}. */
    String content() {
        return contentTr != null ? contentTr : contentEn;
    }
}
