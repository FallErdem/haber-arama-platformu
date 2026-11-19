package com.erdemgural.newssearch.identity;

/**
 * Yöneticinin bir kullanıcıda yaptığı rol veya durum değişikliği (FG-YP-02). Verilmeyen alan değişmez.
 *
 * @param status yalnızca {@code ACTIVE} veya {@code PASSIVE}; onay ve ret ayrı işlemlerdir
 * @param version istemcinin gördüğü kaydın sürümü
 */
public record UserChange(UserRole role, UserStatus status, int version) {}
