package com.erdemgural.newssearch;

import com.erdemgural.newssearch.identity.UserRole;
import com.erdemgural.newssearch.identity.UserStatus;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;

/**
 * Testlerde istenen rol ve durumda hazır kullanıcılar oluşturur ve onlar adına
 * token üretir.
 */
public class TestUsers {

    /** Veritabanında kaydı bulunan bir test kullanıcısı ve onun token'ı. */
    public record TestUser(String keycloakSub, String token) {}

    private final TestTokenIssuer tokenIssuer;
    private final JdbcClient jdbcClient;

    TestUsers(TestTokenIssuer tokenIssuer, JdbcClient jdbcClient) {
        this.tokenIssuer = tokenIssuer;
        this.jdbcClient = jdbcClient;
    }

    public TestUser create(UserRole role, UserStatus status) {
        String keycloakSub = UUID.randomUUID().toString();
        jdbcClient
                .sql("""
				INSERT INTO users (keycloak_sub, email, display_name, role, status)
				VALUES (:keycloakSub, :email, :displayName, :role, :status)
				""")
                .param("keycloakSub", keycloakSub)
                .param("email", keycloakSub + "@example.test")
                .param("displayName", "Test Kullanıcı")
                .param("role", role.name())
                .param("status", status.name())
                .update();
        return new TestUser(keycloakSub, tokenIssuer.token(claims -> claims.subject(keycloakSub)));
    }

    public void changeStatus(TestUser user, UserStatus status) {
        jdbcClient
                .sql("UPDATE users SET status = :status WHERE keycloak_sub = :keycloakSub")
                .param("status", status.name())
                .param("keycloakSub", user.keycloakSub())
                .update();
    }
}
