package com.erdemgural.newssearch.identity;

import java.util.UUID;

/**
 * İsteği yapan kullanıcı. Kimliği token'dan, rolü ve durumu her istekte
 * {@code users} tablosundan gelir (ADR-0014).
 */
public record CurrentUser(UUID id, String email, String displayName, UserRole role, UserStatus status) {
}
