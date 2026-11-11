package com.erdemgural.newssearch;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.test.context.DynamicPropertyRegistrar;
import org.testcontainers.postgresql.PostgreSQLContainer;

/**
 * Testler için geçici bir PostgreSQL konteyneri açar ve uygulamanın veritabanı
 * ayarlarını bu konteynere yönlendirir.
 */
@TestConfiguration(proxyBeanMethods = false)
public class TestDatabaseConfiguration {

	@Bean
	PostgreSQLContainer postgresContainer() {
		return new PostgreSQLContainer("postgres:18.4-trixie")
				.withDatabaseName("news")
				.withEnv("POSTGRES_INITDB_ARGS", "--encoding=UTF8 --locale=C")
				.withInitScript("db/create-roles.sql");
	}

	@Bean
	DynamicPropertyRegistrar databaseProperties(PostgreSQLContainer postgresContainer) {
		return registry -> {
			registry.add("DB_URL", postgresContainer::getJdbcUrl);
			registry.add("DB_APP_PASSWORD", () -> "test-app");
			registry.add("DB_OWNER_PASSWORD", () -> "test-owner");
		};
	}

}
