package com.erdemgural.newssearch.identity.internal;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.Optional;
import java.util.UUID;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

import com.erdemgural.newssearch.identity.CurrentUser;
import com.erdemgural.newssearch.identity.UserRole;
import com.erdemgural.newssearch.identity.UserStatus;

@Repository
class UserRepository {

	private final JdbcClient jdbcClient;

	UserRepository(JdbcClient jdbcClient) {
		this.jdbcClient = jdbcClient;
	}

	Optional<CurrentUser> findByKeycloakSub(String keycloakSub) {
		return jdbcClient.sql("""
				SELECT id, email, display_name, role, status
				FROM users
				WHERE keycloak_sub = :keycloakSub
				""")
				.param("keycloakSub", keycloakSub)
				.query(UserRepository::mapRow)
				.optional();
	}

	/**
	 * Aynı kullanıcının ilk iki isteği aynı anda gelebilir; ON CONFLICT sayesinde
	 * ikinci ekleme hata vermeden atlanır ve tek kayıt oluşur.
	 */
	void insertIfAbsent(String keycloakSub, String email, String displayName, UserRole role, UserStatus status) {
		jdbcClient.sql("""
				INSERT INTO users (keycloak_sub, email, display_name, role, status)
				VALUES (:keycloakSub, :email, :displayName, :role, :status)
				ON CONFLICT (keycloak_sub) DO NOTHING
				""")
				.param("keycloakSub", keycloakSub)
				.param("email", email)
				.param("displayName", displayName)
				.param("role", role.name())
				.param("status", status.name())
				.update();
	}

	private static CurrentUser mapRow(ResultSet row, int rowNumber) throws SQLException {
		return new CurrentUser(
				row.getObject("id", UUID.class),
				row.getString("email"),
				row.getString("display_name"),
				UserRole.valueOf(row.getString("role")),
				UserStatus.valueOf(row.getString("status")));
	}

}
