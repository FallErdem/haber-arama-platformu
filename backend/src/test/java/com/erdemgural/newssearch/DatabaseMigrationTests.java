package com.erdemgural.newssearch;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.simple.JdbcClient;

@SpringBootTest
@Import({TestDatabaseConfiguration.class, TestElasticsearchConfiguration.class})
class DatabaseMigrationTests {

    private final JdbcClient jdbcClient;

    @Autowired
    DatabaseMigrationTests(JdbcClient jdbcClient) {
        this.jdbcClient = jdbcClient;
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
}
