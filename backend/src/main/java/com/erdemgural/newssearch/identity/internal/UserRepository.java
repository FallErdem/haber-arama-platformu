package com.erdemgural.newssearch.identity.internal;

import com.erdemgural.newssearch.identity.CurrentUser;
import com.erdemgural.newssearch.identity.UserRole;
import com.erdemgural.newssearch.identity.UserStatus;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class UserRepository {

    /**
     * Kayıtlı kullanıcı ve son oturum kimliği. Oturum kimliği yalnızca yeni oturumu fark etmek için
     * okunur (ADR-0016); modül dışına verilen {@link CurrentUser}'da yoktur.
     */
    record StoredUser(CurrentUser user, String lastSessionId) {}

    private final JdbcClient jdbcClient;

    UserRepository(JdbcClient jdbcClient) {
        this.jdbcClient = jdbcClient;
    }

    Optional<StoredUser> findByKeycloakSub(String keycloakSub) {
        return jdbcClient
                .sql("""
				SELECT id, email, display_name, role, status, last_session_id
				FROM users
				WHERE keycloak_sub = :keycloakSub
				""")
                .param("keycloakSub", keycloakSub)
                .query((row, rowNumber) -> new StoredUser(mapRow(row), row.getString("last_session_id")))
                .optional();
    }

    /**
     * Aynı kullanıcının ilk iki isteği aynı anda gelebilir; ON CONFLICT sayesinde
     * ikinci ekleme hata vermeden atlanır ve tek kayıt oluşur.
     *
     * @return kaydı bu çağrı eklediyse {@code true}; aynı anda gelen diğer istek eklediyse {@code false}
     */
    boolean insertIfAbsent(String keycloakSub, String email, String displayName, UserRole role, UserStatus status) {
        int inserted = jdbcClient
                .sql("""
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
        return inserted == 1;
    }

    /**
     * Kullanıcının son oturum kimliğini günceller; kimlik zaten buysa bir şey değiştirmez. Güncelleme
     * koşulludur: aynı yeni oturumla aynı anda gelen iki istekten yalnızca biri satırı değiştirir, diğeri
     * satırın kilidini bekler ve koşul artık sağlanmadığı için hiçbir satırı değiştirmez.
     *
     * @return satırı bu çağrı değiştirdiyse {@code true}: yeni oturumun kaydını bu istek yazar
     */
    boolean startSession(UUID userId, String sessionId) {
        int updated = jdbcClient
                .sql("""
				UPDATE users
				SET last_session_id = :sessionId
				WHERE id = :userId
				  AND last_session_id IS DISTINCT FROM :sessionId
				""")
                .param("userId", userId)
                .param("sessionId", sessionId)
                .update();
        return updated == 1;
    }

    private static CurrentUser mapRow(ResultSet row) throws SQLException {
        return new CurrentUser(
                row.getObject("id", UUID.class),
                row.getString("email"),
                row.getString("display_name"),
                UserRole.valueOf(row.getString("role")),
                UserStatus.valueOf(row.getString("status")));
    }
}
