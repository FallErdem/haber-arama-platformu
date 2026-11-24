package com.erdemgural.newssearch.audit.internal;

import static org.assertj.core.api.Assertions.assertThat;

import com.erdemgural.newssearch.TestDatabaseConfiguration;
import com.erdemgural.newssearch.TestKeycloakConfiguration;
import com.erdemgural.newssearch.TestMediaUrls;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * Audit tablosu aylara bölümlenmiştir (V8). Arama yalnızca istenen tarih aralığına düşen bölümlere bakmalıdır;
 * yoksa kayıtlar arttıkça eski bir ay arandığında daha yeni ayların bütün kayıtları okunup atılır (FOG-43).
 * Bu testte Elasticsearch ve MinIO gerekmez; adresleri kimsenin dinlemediği bir porttur.
 */
@SpringBootTest(
        properties = {
            "ES_URL=http://127.0.0.1:9",
            "ES_PASSWORD=kullanilmiyor",
            "MINIO_URL=http://127.0.0.1:9",
            "MINIO_SECRET_KEY=kullanilmiyor",
            "MEDIA_SIGNING_KEY=" + TestMediaUrls.SIGNING_KEY
        })
@Import({TestDatabaseConfiguration.class, TestKeycloakConfiguration.class})
class AuditEventQueryPlanTests {

    private final JdbcClient jdbcClient;
    private final TransactionTemplate transactionTemplate;

    @Autowired
    AuditEventQueryPlanTests(JdbcClient jdbcClient, TransactionTemplate transactionTemplate) {
        this.jdbcClient = jdbcClient;
        this.transactionTemplate = transactionTemplate;
    }

    @Test
    @DisplayName("audit araması yalnızca istenen aralığa düşen aylık bölümlere bakar")
    void searchReadsOnlyPartitionsInTheRequestedRange() {
        // Repository'nin sorgusu; adlı parametreler PREPARE'in beklediği sıra numaralarına çevrilir.
        String query = (AuditEventRepository.SELECT
                        + AuditEventRepository.FILTER
                        + AuditEventRepository.ORDER
                        + " LIMIT 50")
                .replace(":from", "$1")
                .replace(":to", "$2")
                .replace(":actorUserId", "$3")
                .replace(":action", "$4")
                .replace(":targetType", "$5")
                .replace(":targetId", "$6")
                .replace(":result", "$7");

        List<String> plan = transactionTemplate.execute(status -> {
            // Uygulama aynı sorguyu tekrar tekrar çalıştırdıkça PostgreSQL genel plana geçebilir: parametrelerin
            // değerleri planlanırken bilinmez, bölümler sorgu başlarken atlanır. Test bu durumu zorlar.
            jdbcClient.sql("SET LOCAL plan_cache_mode = force_generic_plan").update();
            jdbcClient.sql("PREPARE audit_search AS " + query).update();
            try {
                return jdbcClient
                        .sql("EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY OFF) EXECUTE audit_search("
                                + "'2027-06-01T00:00:00Z', '2027-06-30T23:59:59Z', NULL, NULL, NULL, NULL, NULL)")
                        .query(String.class)
                        .list();
            } finally {
                jdbcClient.sql("DEALLOCATE audit_search").update();
            }
        });

        assertThat(String.join("\n", plan))
                .contains("audit_events_2027_06")
                .doesNotContain("audit_events_2027_05")
                .doesNotContain("audit_events_2027_07");
    }
}
