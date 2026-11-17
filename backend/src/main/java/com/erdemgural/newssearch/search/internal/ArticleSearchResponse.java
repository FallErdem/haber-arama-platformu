package com.erdemgural.newssearch.search.internal;

import java.util.List;

/**
 * Arama yanıtı: sayfalı liste (API sözleşmesi 2.4).
 *
 * @param totalElements eşleşen haber sayısı; en fazla 10.000
 * @param totalRelation {@code eq}: sayı kesin; {@code gte}: gerçek sayı daha büyük olabilir
 */
record ArticleSearchResponse(
        List<ArticleSearchItem> items, int page, int size, long totalElements, int totalPages, String totalRelation) {}
