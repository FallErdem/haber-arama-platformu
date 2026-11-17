package com.erdemgural.newssearch.search;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch._types.ElasticsearchException;
import com.erdemgural.newssearch.TestDatabaseConfiguration;
import com.erdemgural.newssearch.TestElasticsearchConfiguration;
import com.erdemgural.newssearch.TestKeycloakConfiguration;
import com.erdemgural.newssearch.TestSearchIndex;
import com.erdemgural.newssearch.TestStorageConfiguration;
import java.io.IOException;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;

/**
 * Uygulamanın Elasticsearch bağlantısı ve yetkisi: {@code news_api} kullanıcısı arama indeksini
 * okuyabilir ama değiştiremez (en az yetki; indeksi Python işçisi yönetir).
 */
@SpringBootTest
// Diğer API testleriyle aynı yapılandırma: Spring aynı uygulamayı ve aynı konteynerleri yeniden kullanır.
@AutoConfigureMockMvc
@Import({
    TestDatabaseConfiguration.class,
    TestKeycloakConfiguration.class,
    TestElasticsearchConfiguration.class,
    TestStorageConfiguration.class
})
class SearchIndexAccessTests {

    private static final String NOVEMBER_INDEX = "articles-g1-2026.11.01";

    private final ElasticsearchClient client;
    private final TestSearchIndex searchIndex;

    @Autowired
    SearchIndexAccessTests(ElasticsearchClient client, TestSearchIndex searchIndex) {
        this.client = client;
        this.searchIndex = searchIndex;
    }

    @BeforeEach
    void startWithOneArticle() {
        searchIndex.clear();
        searchIndex.index(NOVEMBER_INDEX, "haber-1", """
                {"language": "tr", "title_tr": "İstanbul'da kitap fuarı açıldı"}
                """);
    }

    @Test
    @DisplayName("uygulama arama indeksini takma ad üzerinden okuyabilir")
    void applicationCanReadThroughTheAlias() throws IOException {
        long count = client.count(request -> request.index("articles")).count();

        assertThat(count).isEqualTo(1);
    }

    @Test
    @DisplayName("test indeksi işçinin kurduğu yapıyı taşır: Türkçe karaktersiz sorgu katlanmış alt alanda bulunur")
    void testIndexCarriesTheWorkersStructure() throws IOException {
        long inMainField = client.count(request -> request.index("articles")
                        .query(query ->
                                query.match(match -> match.field("title_tr").query("ISTANBUL"))))
                .count();
        long inFoldedField = client.count(request -> request.index("articles")
                        .query(query -> query.match(
                                match -> match.field("title_tr.folded").query("ISTANBUL"))))
                .count();

        assertThat(inMainField).isZero();
        assertThat(inFoldedField).isEqualTo(1);
    }

    @Test
    @DisplayName("uygulama arama indeksine yazamaz: belge ekleme 403 ile reddedilir")
    void applicationCannotWriteDocuments() {
        assertThatThrownBy(() -> client.index(
                        request -> request.index(NOVEMBER_INDEX).id("haber-2").document(Map.of("language", "tr"))))
                .isInstanceOfSatisfying(
                        ElasticsearchException.class,
                        exception -> assertThat(exception.status()).isEqualTo(403));
    }

    @Test
    @DisplayName("uygulama arama indeksini silemez: silme 403 ile reddedilir")
    void applicationCannotDeleteIndices() {
        assertThatThrownBy(() -> client.indices().delete(request -> request.index(NOVEMBER_INDEX)))
                .isInstanceOfSatisfying(
                        ElasticsearchException.class,
                        exception -> assertThat(exception.status()).isEqualTo(403));
    }
}
