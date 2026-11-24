package com.erdemgural.newssearch.ingestion;

import static org.assertj.core.api.Assertions.assertThat;

import com.erdemgural.newssearch.TestDatabaseConfiguration;
import com.erdemgural.newssearch.TestElasticsearchConfiguration;
import com.erdemgural.newssearch.TestKeycloakConfiguration;
import com.erdemgural.newssearch.TestStorageConfiguration;
import com.erdemgural.newssearch.TestUsers;
import com.erdemgural.newssearch.TestUsers.TestUser;
import com.erdemgural.newssearch.identity.UserRole;
import com.erdemgural.newssearch.identity.UserStatus;
import org.assertj.core.api.InstanceOfAssertFactories;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.assertj.MvcTestResult;

/** Arama filtrelerinin seçenekleri: kaynak ve kategori listeleri (API sözleşmesi 4.3). */
@SpringBootTest
@AutoConfigureMockMvc
@Import({
    TestDatabaseConfiguration.class,
    TestKeycloakConfiguration.class,
    TestElasticsearchConfiguration.class,
    TestStorageConfiguration.class
})
class SourceAndCategoryListTests {

    private static final String SOURCES_PATH = "/api/v1/sources";
    private static final String CATEGORIES_PATH = "/api/v1/categories";

    private final MockMvcTester mvc;
    private final TestUsers users;
    private final JdbcClient jdbcClient;

    @Autowired
    SourceAndCategoryListTests(MockMvcTester mvc, TestUsers users, JdbcClient jdbcClient) {
        this.mvc = mvc;
        this.users = users;
        this.jdbcClient = jdbcClient;
    }

    @Test
    @DisplayName("aktif kullanıcı kaynakları kodu, adı ve diliyle, ada göre sıralı alır")
    void activeUserGetsSourcesOrderedByName() {
        MvcTestResult result = get(SOURCES_PATH, activeUser());

        assertThat(result).hasStatusOk();
        // Başlangıç verisi: V11'in 4, V19'un 16 ve V22'nin 1 (NYT) kaynağı.
        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[*].code")
                .asArray()
                .hasSize(21)
                .contains("CNNTURK", "GLOBALVOICES", "NTV", "TRT", "HURRIYET", "SPUTNIK", "NYT");
        // Veritabanının sıralama kuralı C (kod noktası sırası); Java'nın metin karşılaştırmasıyla aynıdır.
        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[*].name")
                .asInstanceOf(InstanceOfAssertFactories.list(String.class))
                .isSorted();
        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[?(@.code == 'CNNTURK')].name")
                .asArray()
                .containsExactly("CNN Türk");
        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[?(@.code == 'GLOBALVOICES')].language")
                .asArray()
                .containsExactly("en");
    }

    @Test
    @DisplayName("kaynak yanıtında yalnızca sözleşmedeki alanlar bulunur")
    void sourceItemExposesOnlyContractFields() {
        MvcTestResult result = get(SOURCES_PATH, activeUser());

        // Kimlik, lisans veya istek aralığı gibi iç alanlar dışarı verilmez.
        assertThat(result).bodyJson().extractingPath("$.items[0]").asMap().containsOnlyKeys("code", "name", "language");
    }

    @Test
    @DisplayName("devre dışı bırakılan kaynak listede yer almaz")
    void disabledSourceIsNotListed() {
        setSourceEnabled("NTV", false);
        try {
            MvcTestResult result = get(SOURCES_PATH, activeUser());

            assertThat(result)
                    .bodyJson()
                    .extractingPath("$.items[*].code")
                    .asArray()
                    .hasSize(20)
                    .contains("CNNTURK", "GLOBALVOICES", "TRT")
                    .doesNotContain("NTV");
        } finally {
            // Testler aynı veritabanını paylaşır; kaynak diğer testler için yeniden etkinleştirilir.
            setSourceEnabled("NTV", true);
        }
    }

    @Test
    @DisplayName("aktif kullanıcı kategorileri arayüzde gösterilecekleri sırayla alır")
    void activeUserGetsCategoriesInDisplayOrder() {
        MvcTestResult result = get(CATEGORIES_PATH, activeUser());

        assertThat(result).hasStatusOk();
        // Başlangıç verisi (V10): on kategori, sort_order sırasıyla.
        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[*].code")
                .asArray()
                .containsExactly(
                        "GENERAL",
                        "WORLD",
                        "ECONOMY",
                        "SPORTS",
                        "HEALTH",
                        "SCIENCE_TECH",
                        "CULTURE_ARTS",
                        "LIFESTYLE",
                        "BREAKING",
                        "OTHER");
    }

    @Test
    @DisplayName("kategori yanıtında kod, tür ve sıra bulunur; Son Dakika süreli etikettir")
    void categoryItemCarriesKindAndSortOrder() {
        MvcTestResult result = get(CATEGORIES_PATH, activeUser());

        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[0]")
                .asMap()
                .containsOnlyKeys("code", "kind", "sortOrder");
        assertThat(result).bodyJson().extractingPath("$.items[0].kind").isEqualTo("TOPIC");
        assertThat(result).bodyJson().extractingPath("$.items[0].sortOrder").isEqualTo(10);
        assertThat(result).bodyJson().extractingPath("$.items[8].kind").isEqualTo("TEMPORAL");
    }

    @Test
    @DisplayName("token olmadan gelen istek 401 ile reddedilir")
    void requestWithoutTokenIsRejected() {
        assertThat(mvc.get().uri(SOURCES_PATH)).hasStatus(HttpStatus.UNAUTHORIZED);
        assertThat(mvc.get().uri(CATEGORIES_PATH)).hasStatus(HttpStatus.UNAUTHORIZED);
    }

    @Test
    @DisplayName("onay bekleyen kullanıcı listeleri alamaz")
    void pendingUserIsRejected() {
        TestUser pending = users.create(UserRole.USER, UserStatus.PENDING);

        assertThat(get(SOURCES_PATH, pending)).hasStatus(HttpStatus.FORBIDDEN);
        assertThat(get(CATEGORIES_PATH, pending)).hasStatus(HttpStatus.FORBIDDEN);
    }

    private TestUser activeUser() {
        return users.create(UserRole.USER, UserStatus.ACTIVE);
    }

    private MvcTestResult get(String path, TestUser user) {
        return mvc.get()
                .uri(path)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + user.token())
                .exchange();
    }

    private void setSourceEnabled(String code, boolean enabled) {
        jdbcClient
                .sql("UPDATE sources SET enabled = :enabled WHERE code = :code")
                .param("enabled", enabled)
                .param("code", code)
                .update();
    }
}
