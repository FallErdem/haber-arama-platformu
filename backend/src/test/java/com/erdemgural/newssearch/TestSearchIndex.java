package com.erdemgural.newssearch;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.Base64;

/**
 * Test Elasticsearch'ünü kümedeki gibi hazırlar ve testlere indeksi doldurma yolu verir.
 *
 * <p>Kümede bu işleri başkaları yapar: {@code news_api} rolünü ve kullanıcısını
 * elasticsearch-setup Job'u oluşturur, indeks şablonunu ve belgeleri Python işçisi yazar.
 * Uygulamanın kendisi yalnızca okur; bu sınıf yazma işlerini süper kullanıcıyla yapar.
 */
public class TestSearchIndex {

    static final String API_PASSWORD = "test-search-api";

    /** Kümedeki rol tanımının aynısı (deploy/k8s/base/elasticsearch/setup-job.yaml): yalnızca okuma. */
    private static final String API_ROLE = """
            {
              "cluster": ["monitor"],
              "indices": [{
                "names": ["articles-*", "articles"],
                "privileges": ["read", "view_index_metadata"]
              }]
            }
            """;

    /**
     * İşçinin kurduğu indeks yapısının (alanlar, analizörler) kopyası. İşçideki bir test, bu
     * dosyanın işçinin tanımıyla aynı olduğunu denetler (R-36).
     */
    private static final String STRUCTURE_RESOURCE = "/search/articles-index-structure.json";

    private final String url;
    private final String authorization;
    private final HttpClient httpClient = HttpClient.newHttpClient();

    TestSearchIndex(String url, String elasticPassword) {
        this.url = url;
        this.authorization = "Basic "
                + Base64.getEncoder().encodeToString(("elastic:" + elasticPassword).getBytes(StandardCharsets.UTF_8));
    }

    public String url() {
        return url;
    }

    /** Rolü, kullanıcıyı ve indeks şablonunu oluşturur. */
    void setUp() {
        send("PUT", "/_security/role/news_api", API_ROLE);
        send("PUT", "/_security/user/news_api", """
                {"password": "%s", "roles": ["news_api"]}
                """.formatted(API_PASSWORD));
        // Yapı dosyası olduğu gibi bir bileşen şablonuna konur; indeks şablonu onu kullanır ve işçinin
        // şablonundaki gibi 1. neslin indekslerini açılırken "articles" takma adına ekler.
        send("PUT", "/_component_template/articles-structure", """
                {"template": %s}
                """.formatted(readResource(STRUCTURE_RESOURCE)));
        send("PUT", "/_index_template/articles-g1", """
                {
                  "index_patterns": ["articles-g1-*"],
                  "composed_of": ["articles-structure"],
                  "template": {
                    "settings": {"number_of_shards": 1, "number_of_replicas": 0},
                    "aliases": {"articles": {}}
                  }
                }
                """);
    }

    /** Bir belgeyi yazar ve hemen aranabilir kılar. */
    public void index(String indexName, String id, String documentJson) {
        send("PUT", "/" + indexName + "/_doc/" + id + "?refresh=true", documentJson);
    }

    /** Bütün haber indekslerini siler; her test boş bir indeksle başlar. */
    public void clear() {
        String names = send("GET", "/_cat/indices/articles-*?h=index&expand_wildcards=all", null)
                .strip();
        if (!names.isEmpty()) {
            // Elasticsearch joker karakterle silmeye izin vermez; indeksler adlarıyla silinir.
            send("DELETE", "/" + String.join(",", names.split("\\s+")), null);
        }
    }

    private String send(String method, String path, String body) {
        HttpRequest.Builder request = HttpRequest.newBuilder(URI.create(url + path))
                .header("Authorization", authorization)
                .header("Content-Type", "application/json");
        request.method(
                method,
                body == null
                        ? HttpRequest.BodyPublishers.noBody()
                        : HttpRequest.BodyPublishers.ofString(body, StandardCharsets.UTF_8));
        try {
            HttpResponse<String> response = httpClient.send(request.build(), HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() >= 300) {
                throw new IllegalStateException("Elasticsearch isteği başarısız: %s %s -> %d %s"
                        .formatted(method, path, response.statusCode(), response.body()));
            }
            return response.body();
        } catch (IOException exception) {
            throw new UncheckedIOException(exception);
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(exception);
        }
    }

    private static String readResource(String path) {
        try (InputStream stream = TestSearchIndex.class.getResourceAsStream(path)) {
            if (stream == null) {
                throw new IllegalStateException("Test kaynağı bulunamadı: " + path);
            }
            return new String(stream.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException exception) {
            throw new UncheckedIOException(exception);
        }
    }
}
