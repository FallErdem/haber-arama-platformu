package com.erdemgural.newssearch;

import static org.assertj.core.api.Assertions.assertThat;

import com.erdemgural.newssearch.TestUsers.TestUser;
import com.erdemgural.newssearch.identity.UserRole;
import com.erdemgural.newssearch.identity.UserStatus;
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

/**
 * Elasticsearch'e ulaşılamadığında uygulamanın geri kalanı çalışmaya devam eder (FOG-09).
 * Bu testte Elasticsearch konteyneri yoktur; adres kimsenin dinlemediği bir porttur.
 */
@SpringBootTest(properties = {"ES_URL=http://127.0.0.1:9", "ES_PASSWORD=kullanilmiyor"})
@AutoConfigureMockMvc
@Import({TestDatabaseConfiguration.class, TestKeycloakConfiguration.class})
class ElasticsearchUnavailableTests {

    private final MockMvcTester mvc;
    private final TestUsers users;

    @Autowired
    ElasticsearchUnavailableTests(MockMvcTester mvc, TestUsers users) {
        this.mvc = mvc;
        this.users = users;
    }

    @Test
    @DisplayName("Elasticsearch kapalıyken uygulama açılır ve Kubernetes'in sağlık kontrolleri geçer")
    void probesStayHealthyWithoutElasticsearch() {
        // Kontroller geçmeseydi Kubernetes pod'u yeniden başlatır veya istek göndermeyi keserdi;
        // Elasticsearch'in kapalı olması aramayla ilgisi olmayan işlevleri de durdurmuş olurdu.
        assertThat(mvc.get().uri("/actuator/health/liveness")).hasStatusOk();
        assertThat(mvc.get().uri("/actuator/health/readiness")).hasStatusOk();
    }

    @Test
    @DisplayName("Elasticsearch kapalıyken aramayla ilgisi olmayan uç noktalar çalışır")
    void otherEndpointsWorkWithoutElasticsearch() {
        TestUser user = users.create(UserRole.USER, UserStatus.ACTIVE);

        assertThat(mvc.get()
                        .uri("/api/v1/sources")
                        .header(HttpHeaders.AUTHORIZATION, "Bearer " + user.token())
                        .exchange())
                .hasStatusOk();
    }

    @Test
    @DisplayName("Elasticsearch kapalıyken arama 503 ve SEARCH_UNAVAILABLE döner; iç ayrıntı vermez")
    void searchReportsThatItIsUnavailable() {
        TestUser user = users.create(UserRole.USER, UserStatus.ACTIVE);

        MvcTestResult result = mvc.get()
                .uri("/api/v1/articles")
                .param("q", "deprem")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + user.token())
                .exchange();

        assertThat(result).hasStatus(HttpStatus.SERVICE_UNAVAILABLE);
        assertThat(result).hasContentType("application/problem+json");
        assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("SEARCH_UNAVAILABLE");
        assertThat(result).bodyText().doesNotContain("Connection", "127.0.0.1", "Exception");
    }
}
