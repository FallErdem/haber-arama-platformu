package com.erdemgural.newssearch.ingestion.internal;

/**
 * {@code GET /api/v1/sources} yanıtındaki bir kaynak (API sözleşmesi 4.3). Kaynaklar
 * kimlikleriyle değil kodlarıyla gösterilir (sözleşme 2.3).
 */
record SourceResponse(String code, String name, String language) {}
