package com.erdemgural.newssearch.ingestion.internal;

/**
 * {@code GET /api/v1/categories} yanıtındaki bir kategori (API sözleşmesi 4.3). Görünen ad
 * burada yoktur; arayüz adı kendi dil dosyalarından koda göre bulur (FOG-31).
 *
 * @param kind {@code TOPIC} (konu) veya {@code TEMPORAL} (Son Dakika gibi süreli etiket)
 */
record CategoryResponse(String code, String kind, int sortOrder) {}
