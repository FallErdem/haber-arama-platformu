package com.erdemgural.newssearch.identity;

/**
 * Kullanıcı listesinin filtreleri; {@code null} alan filtrelenmez.
 *
 * @param query e-postada veya görünen adda, büyük/küçük harf ayrımı yapılmadan aranan metin
 */
public record UserFilter(UserStatus status, UserRole role, String query) {}
