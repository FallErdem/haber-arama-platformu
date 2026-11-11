package com.erdemgural.newssearch;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.context.DynamicPropertyRegistrar;

/**
 * Testlerde uygulamanın Keycloak ayarlarını {@link TestTokenIssuer}'a yönlendirir.
 */
@TestConfiguration(proxyBeanMethods = false)
public class TestKeycloakConfiguration {

	public static final String INITIAL_ADMIN_EMAIL = "yonetici@example.test";

	@Bean(destroyMethod = "stop")
	TestTokenIssuer testTokenIssuer() {
		return new TestTokenIssuer();
	}

	@Bean
	TestUsers testUsers(TestTokenIssuer testTokenIssuer, JdbcClient jdbcClient) {
		return new TestUsers(testTokenIssuer, jdbcClient);
	}

	@Bean
	DynamicPropertyRegistrar keycloakProperties(TestTokenIssuer testTokenIssuer) {
		return registry -> {
			registry.add("KEYCLOAK_JWKS_URL", testTokenIssuer::jwksUrl);
			registry.add("INITIAL_ADMIN_EMAIL", () -> INITIAL_ADMIN_EMAIL);
		};
	}

}
