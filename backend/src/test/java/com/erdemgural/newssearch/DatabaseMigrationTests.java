package com.erdemgural.newssearch;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.testcontainers.postgresql.PostgreSQLContainer;

@SpringBootTest
@Import({TestDatabaseConfiguration.class, TestElasticsearchConfiguration.class, TestStorageConfiguration.class})
class DatabaseMigrationTests {

    private final JdbcClient jdbcClient;
    private final PostgreSQLContainer postgres;

    @Autowired
    DatabaseMigrationTests(JdbcClient jdbcClient, PostgreSQLContainer postgres) {
        this.jdbcClient = jdbcClient;
        this.postgres = postgres;
    }

    @Test
    @DisplayName("uygulama veritabanına news_app kullanıcısıyla bağlanır")
    void applicationConnectsAsApplicationUser() {
        String currentUser =
                jdbcClient.sql("SELECT current_user").query(String.class).single();

        assertThat(currentUser).isEqualTo("news_app");
    }

    @Test
    @DisplayName("geçiş betikleri uygulanır ve news_app başlangıç verisini okuyabilir")
    void migrationsAreAppliedAndSeedDataIsReadable() {
        Long categoryCount = jdbcClient
                .sql("SELECT count(*) FROM categories")
                .query(Long.class)
                .single();
        Long feedCount =
                jdbcClient.sql("SELECT count(*) FROM feeds").query(Long.class).single();

        assertThat(categoryCount).isEqualTo(10);
        assertThat(feedCount).isEqualTo(42);
    }

    @Test
    @DisplayName("news_app tablo oluşturamaz")
    void applicationUserCannotCreateTables() {
        assertThatThrownBy(() -> jdbcClient
                        .sql("CREATE TABLE should_not_exist (id integer)")
                        .update())
                .isInstanceOf(DataAccessException.class)
                .rootCause()
                .hasMessageContaining("permission denied");
    }

    @Test
    @DisplayName("yedekleme kullanıcısı (news_backup) bağlanır ve bütün tabloları okur, hiçbir şeyi değiştiremez")
    void backupUserCanReadEverythingButChangeNothing() throws SQLException {
        // Şifre test rolünündür (src/test/resources/db/create-roles.sql).
        try (Connection connection = DriverManager.getConnection(postgres.getJdbcUrl(), "news_backup", "test-backup");
                Statement statement = connection.createStatement()) {
            // Kullanıcı tabloları ve audit kayıtları da okunur; işçi bunları okuyamaz.
            assertThat(count(statement, "users")).isNotNegative();
            assertThat(count(statement, "audit_events")).isNotNegative();
            assertThat(count(statement, "categories")).isEqualTo(10);

            assertThatThrownBy(() -> statement.executeUpdate("DELETE FROM categories"))
                    .isInstanceOf(SQLException.class)
                    .hasMessageContaining("permission denied");
        }
    }

    private static long count(Statement statement, String table) throws SQLException {
        try (ResultSet result = statement.executeQuery("SELECT count(*) FROM " + table)) {
            result.next();
            return result.getLong(1);
        }
    }
}
