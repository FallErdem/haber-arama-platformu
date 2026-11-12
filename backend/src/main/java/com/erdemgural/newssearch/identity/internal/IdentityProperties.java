package com.erdemgural.newssearch.identity.internal;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Kimlik modülünün ayarları ({@code newssearch.identity.*}).
 *
 * @param initialAdminEmail ilk yöneticinin e-posta adresi; boşsa kimse
 *                          kendiliğinden yönetici olmaz
 */
@ConfigurationProperties("newssearch.identity")
record IdentityProperties(String initialAdminEmail) {}
