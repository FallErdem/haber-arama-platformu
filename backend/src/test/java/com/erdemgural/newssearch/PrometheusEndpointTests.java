package com.erdemgural.newssearch;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.micrometer.metrics.test.autoconfigure.AutoConfigureMetrics;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.servlet.assertj.MockMvcTester;

/**
 * Prometheus'un ölçümleri okuduğu adres (FOG-40). Spring Boot testlerde ölçüm yayımlamayı kapatır;
 * {@code @AutoConfigureMetrics} onu açar. Bu testte Elasticsearch ve MinIO gerekmez; adresleri
 * kimsenin dinlemediği bir porttur (bkz. {@link UnavailableServicesTests}).
 */
@SpringBootTest(
        properties = {
            "ES_URL=http://127.0.0.1:9",
            "ES_PASSWORD=kullanilmiyor",
            "MINIO_URL=http://127.0.0.1:9",
            "MINIO_SECRET_KEY=kullanilmiyor",
            "MEDIA_SIGNING_KEY=" + TestMediaUrls.SIGNING_KEY
        })
@AutoConfigureMockMvc
@AutoConfigureMetrics
@Import({TestDatabaseConfiguration.class, TestKeycloakConfiguration.class})
class PrometheusEndpointTests {

    private final MockMvcTester mvc;

    @Autowired
    PrometheusEndpointTests(MockMvcTester mvc) {
        this.mvc = mvc;
    }

    @Test
    @DisplayName("Prometheus adresi token istemez; isteklerin sayısını, durum kodunu ve süre dağılımını içerir")
    void exposesRequestMetricsWithoutToken() {
        // Token'sız istek 401 alır. 401 artışı uyarısı (ADR-0016) bu sayıya bakar.
        assertThat(mvc.get().uri("/api/v1/articles")).hasStatus(HttpStatus.UNAUTHORIZED);

        assertThat(mvc.get().uri("/actuator/prometheus"))
                .hasStatusOk()
                .bodyText()
                .contains("http_server_requests_seconds_count{")
                .contains("status=\"401\"")
                // p95 hesaplanabilsin diye sürelerin dağılımı da yayımlanır.
                .contains("http_server_requests_seconds_bucket{");
    }
}
