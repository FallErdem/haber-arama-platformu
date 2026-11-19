package com.erdemgural.newssearch.admin.internal;

/**
 * {@code PATCH /api/v1/admin/users/{id}} gövdesi. Alanlar metin olarak alınır ve controller'da okunur:
 * geçersiz bir değer de alan adı ve koduyla bildirilir (sözleşme 2.6).
 *
 * @param role {@code USER} veya {@code ADMIN}; verilmezse değişmez
 * @param status {@code ACTIVE} veya {@code PASSIVE}; verilmezse değişmez
 * @param version zorunlu; istemcinin gördüğü kaydın sürümü (sözleşme 2.5)
 */
record UserChangeRequest(String role, String status, Integer version) {}
