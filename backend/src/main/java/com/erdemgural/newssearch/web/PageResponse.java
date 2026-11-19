package com.erdemgural.newssearch.web;

import java.util.List;

/**
 * Sayfalı listelerin yanıtı (API sözleşmesi 2.4).
 *
 * @param totalElements bütün sayfalardaki öğe sayısı
 * @param totalPages sayfa sayısı; liste boşsa 0
 */
public record PageResponse<T>(List<T> items, int page, int size, long totalElements, int totalPages) {

    public static <T> PageResponse<T> of(List<T> items, PageParameters parameters, long totalElements) {
        // Yukarı yuvarlanan bölme: 41 öğe, 20'şerli sayfalarda 3 sayfadır.
        int totalPages = (int) ((totalElements + parameters.size() - 1) / parameters.size());
        return new PageResponse<>(items, parameters.page(), parameters.size(), totalElements, totalPages);
    }
}
