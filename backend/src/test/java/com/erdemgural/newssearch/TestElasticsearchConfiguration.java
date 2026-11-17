package com.erdemgural.newssearch;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.context.DynamicPropertyRegistrar;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.wait.strategy.Wait;

/**
 * Testler için geçici bir Elasticsearch konteyneri açar ve uygulamanın Elasticsearch ayarlarını
 * bu konteynere yönlendirir. Sürüm ve güvenlik ayarları kümedekiyle aynıdır
 * (deploy/k8s/base/elasticsearch): güvenlik açık, TLS yok.
 */
@TestConfiguration(proxyBeanMethods = false)
public class TestElasticsearchConfiguration {

    static final String ELASTIC_PASSWORD = "test-elastic";

    @Bean
    GenericContainer<?> elasticsearchContainer() {
        return new GenericContainer<>("docker.elastic.co/elasticsearch/elasticsearch:9.4.9")
                .withExposedPorts(9200)
                .withEnv("discovery.type", "single-node")
                .withEnv("xpack.security.enabled", "true")
                .withEnv("xpack.security.http.ssl.enabled", "false")
                .withEnv("xpack.security.transport.ssl.enabled", "false")
                .withEnv("ELASTIC_PASSWORD", ELASTIC_PASSWORD)
                .withEnv("ES_JAVA_OPTS", "-Xms512m -Xmx512m")
                .waitingFor(Wait.forHttp("/_cluster/health?wait_for_status=yellow")
                        .forPort(9200)
                        .withBasicCredentials("elastic", ELASTIC_PASSWORD));
    }

    @Bean
    TestSearchIndex testSearchIndex(@Qualifier("elasticsearchContainer") GenericContainer<?> elasticsearchContainer) {
        String url = "http://" + elasticsearchContainer.getHost() + ":" + elasticsearchContainer.getMappedPort(9200);
        TestSearchIndex index = new TestSearchIndex(url, ELASTIC_PASSWORD);
        index.setUp();
        return index;
    }

    @Bean
    TestArticles testArticles(JdbcClient jdbcClient, TestSearchIndex testSearchIndex) {
        return new TestArticles(jdbcClient, testSearchIndex);
    }

    @Bean
    DynamicPropertyRegistrar elasticsearchProperties(TestSearchIndex testSearchIndex) {
        return registry -> {
            registry.add("ES_URL", testSearchIndex::url);
            registry.add("ES_PASSWORD", () -> TestSearchIndex.API_PASSWORD);
        };
    }
}
