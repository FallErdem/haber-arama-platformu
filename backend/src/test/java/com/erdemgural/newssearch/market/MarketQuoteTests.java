package com.erdemgural.newssearch.market;

import static org.assertj.core.api.Assertions.assertThat;

import com.erdemgural.newssearch.TestDatabaseConfiguration;
import com.erdemgural.newssearch.TestElasticsearchConfiguration;
import com.erdemgural.newssearch.TestKeycloakConfiguration;
import com.erdemgural.newssearch.TestStorageConfiguration;
import com.erdemgural.newssearch.TestUsers;
import com.erdemgural.newssearch.TestUsers.TestUser;
import com.erdemgural.newssearch.identity.UserRole;
import com.erdemgural.newssearch.identity.UserStatus;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.Instant;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.assertj.MvcTestResult;
import org.testcontainers.postgresql.PostgreSQLContainer;

/**
 * Piyasa verileri: {@code GET /api/v1/market-quotes} (issue #79). Gerçek PostgreSQL ile. Uygulamanın kullanıcısı
 * ({@code news_app}) tabloya yazamadığı için test verisi konteynerin yönetici kullanıcısıyla eklenir; satırları
 * gerçekte işçi yazar.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import({
    TestDatabaseConfiguration.class,
    TestKeycloakConfiguration.class,
    TestElasticsearchConfiguration.class,
    TestStorageConfiguration.class
})
class MarketQuoteTests {

    private static final String PATH = "/api/v1/market-quotes";
    private static final Instant MARKET_TIME = Instant.parse("2026-11-27T12:30:37Z");
    private static final Instant FETCHED_AT = Instant.parse("2026-11-27T12:31:02Z");

    private final MockMvcTester mvc;
    private final TestUsers users;
    private final PostgreSQLContainer postgres;

    @Autowired
    MarketQuoteTests(MockMvcTester mvc, TestUsers users, PostgreSQLContainer postgres) {
        this.mvc = mvc;
        this.users = users;
        this.postgres = postgres;
    }

    @BeforeEach
    void startEmpty() throws SQLException {
        try (Connection connection = adminConnection();
                Statement statement = connection.createStatement()) {
            statement.execute("DELETE FROM market_quotes");
        }
    }

    @Test
    @DisplayName("değerler sözleşmedeki alanlarla ve önceki kapanışa göre değişim yüzdesiyle döner")
    void quotesAreReturnedWithChangePercent() throws SQLException {
        insertQuote("USD", "50.785", "50.7185", "TRY");
        insertQuote("BRENT", "90.00", "91.50", "USD");

        MvcTestResult result = get(activeUser());

        assertThat(result).hasStatusOk();
        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[*].code")
                .asArray()
                .containsExactly("BRENT", "USD");
        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[1]")
                .asMap()
                .containsOnlyKeys("code", "price", "changePercent", "currency", "marketTime", "fetchedAt");
        assertThat(result).bodyJson().extractingPath("$.items[1].price").isEqualTo(50.785);
        // (50,785 − 50,7185) × 100 ÷ 50,7185 = 0,1311... → 0,13
        assertThat(result).bodyJson().extractingPath("$.items[1].changePercent").isEqualTo(0.13);
        assertThat(result).bodyJson().extractingPath("$.items[1].currency").isEqualTo("TRY");
        assertThat(result).bodyJson().extractingPath("$.items[1].marketTime").isEqualTo("2026-11-27T12:30:37Z");
        assertThat(result).bodyJson().extractingPath("$.items[1].fetchedAt").isEqualTo("2026-11-27T12:31:02Z");
        // Düşüş eksi işaretiyle gelir: (90 − 91,5) × 100 ÷ 91,5 = −1,639... → −1,64
        assertThat(result).bodyJson().extractingPath("$.items[0].changePercent").isEqualTo(-1.64);
    }

    @Test
    @DisplayName("işçi henüz hiç değer yazmadıysa liste boştur")
    void emptyTableGivesEmptyList() {
        MvcTestResult result = get(activeUser());

        assertThat(result).hasStatusOk();
        assertThat(result).bodyJson().extractingPath("$.items").asArray().isEmpty();
    }

    @Test
    @DisplayName("token olmadan gelen istek 401 ile reddedilir")
    void requestWithoutTokenIsRejected() {
        assertThat(mvc.get().uri(PATH)).hasStatus(HttpStatus.UNAUTHORIZED);
    }

    @Test
    @DisplayName("onay bekleyen kullanıcı değerleri alamaz")
    void pendingUserIsRejected() {
        TestUser pending = users.create(UserRole.USER, UserStatus.PENDING);

        assertThat(get(pending)).hasStatus(HttpStatus.FORBIDDEN);
    }

    private TestUser activeUser() {
        return users.create(UserRole.USER, UserStatus.ACTIVE);
    }

    private MvcTestResult get(TestUser user) {
        return mvc.get()
                .uri(PATH)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + user.token())
                .exchange();
    }

    private Connection adminConnection() throws SQLException {
        return DriverManager.getConnection(postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword());
    }

    private void insertQuote(String code, String price, String previousClose, String currency) throws SQLException {
        try (Connection connection = adminConnection();
                PreparedStatement statement = connection.prepareStatement("""
						INSERT INTO market_quotes (code, price, previous_close, currency, market_time, fetched_at)
						VALUES (?, ?::numeric, ?::numeric, ?, ?, ?)
						""")) {
            statement.setString(1, code);
            statement.setString(2, price);
            statement.setString(3, previousClose);
            statement.setString(4, currency);
            statement.setTimestamp(5, Timestamp.from(MARKET_TIME));
            statement.setTimestamp(6, Timestamp.from(FETCHED_AT));
            statement.executeUpdate();
        }
    }
}
