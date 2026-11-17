package com.erdemgural.newssearch;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.context.DynamicPropertyRegistrar;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.wait.strategy.Wait;

/**
 * Testler için geçici bir MinIO açar ve uygulamanın görsel ayarlarını bu konteynere yönlendirir.
 * Sürüm kümedekiyle aynıdır (deploy/k8s/base/minio). Kümede sunucu "-distroless" imajla çalışır;
 * testte kurulum için kabuk ve mc istemcisi gerektiğinden aynı sürümün standart imajı kullanılır.
 */
@TestConfiguration(proxyBeanMethods = false)
public class TestStorageConfiguration {

    static final String ROOT_USER = "test-root";
    static final String ROOT_PASSWORD = "test-root-password";
    static final String API_PASSWORD = "test-storage-api";

    /**
     * API'nin MinIO politikası; kümedekinin aynısı (deploy/k8s/base/minio/setup-job.yaml): yalnızca
     * {@code media} kovasındaki dosyaları okuma.
     */
    private static final String API_POLICY = """
            {"Version": "2012-10-17", "Statement": [
              {"Effect": "Allow", "Action": ["s3:GetObject"], "Resource": ["arn:aws:s3:::media/*"]}
            ]}""";

    @Bean
    GenericContainer<?> minioContainer() {
        return new GenericContainer<>("docker.io/pgsty/silo:RELEASE.2026-10-26T00-00-00Z")
                .withCommand("server", "/data")
                .withExposedPorts(9000)
                .withEnv("MINIO_ROOT_USER", ROOT_USER)
                .withEnv("MINIO_ROOT_PASSWORD", ROOT_PASSWORD)
                .waitingFor(Wait.forHttp("/minio/health/live").forPort(9000));
    }

    @Bean
    TestImages testImages(@Qualifier("minioContainer") GenericContainer<?> minioContainer, JdbcClient jdbcClient)
            throws Exception {
        // Kurulum, kümedeki Job gibi mc ile ve konteynerin içinden yapılır.
        String script = """
                set -e
                mc alias set local http://127.0.0.1:9000 %s %s
                mc mb --ignore-existing local/media
                echo '%s' > /tmp/news-api.json
                mc admin policy create local news-api /tmp/news-api.json
                mc admin user add local news-api %s
                mc admin policy attach local news-api --user news-api
                """.formatted(ROOT_USER, ROOT_PASSWORD, API_POLICY, API_PASSWORD);
        var result = minioContainer.execInContainer("sh", "-c", script);
        if (result.getExitCode() != 0) {
            throw new IllegalStateException("MinIO kurulamadı: " + result.getStdout() + result.getStderr());
        }
        String url = "http://" + minioContainer.getHost() + ":" + minioContainer.getMappedPort(9000);
        return new TestImages(url, ROOT_USER, ROOT_PASSWORD, jdbcClient);
    }

    @Bean
    DynamicPropertyRegistrar storageProperties(TestImages testImages) {
        return registry -> {
            registry.add("MINIO_URL", testImages::url);
            registry.add("MINIO_SECRET_KEY", () -> API_PASSWORD);
            registry.add("MEDIA_SIGNING_KEY", () -> TestMediaUrls.SIGNING_KEY);
        };
    }
}
