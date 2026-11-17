package com.erdemgural.newssearch.search.internal;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/** Arama ifadesinin tırnak içindeki öbekler ve diğer kelimeler olarak ayrılması. */
class SearchTextTests {

    @Test
    @DisplayName("tırnaksız ifade olduğu gibi kelimeler olarak kalır")
    void queryWithoutQuotesIsJustWords() {
        assertThat(SearchText.parse("merkez bankası faiz")).isEqualTo(new SearchText(List.of(), "merkez bankası faiz"));
    }

    @Test
    @DisplayName("tırnak içindeki öbek ayrılır, geri kalan kelimeler korunur")
    void quotedPhraseIsSeparatedFromWords() {
        assertThat(SearchText.parse("\"merkez bankası\" faiz kararı"))
                .isEqualTo(new SearchText(List.of("merkez bankası"), "faiz kararı"));
    }

    @Test
    @DisplayName("birden fazla öbek ve yalnızca öbekten oluşan ifade")
    void severalPhrasesAndPhraseOnlyQuery() {
        assertThat(SearchText.parse("\"beyaz saray\" ve \"dışişleri bakanlığı\""))
                .isEqualTo(new SearchText(List.of("beyaz saray", "dışişleri bakanlığı"), "ve"));
        assertThat(SearchText.parse("\"asgari ücret\"")).isEqualTo(new SearchText(List.of("asgari ücret"), ""));
    }

    @Test
    @DisplayName("telefon klavyelerinin eğik tırnakları da öbek oluşturur")
    void curlyQuotesAlsoMakePhrases() {
        assertThat(SearchText.parse("“yapay zeka” yasası")).isEqualTo(new SearchText(List.of("yapay zeka"), "yasası"));
    }

    @Test
    @DisplayName("kapanmayan tırnak öbek oluşturmaz; işaret atılır, kelimeler normal aranır")
    void unclosedQuoteIsIgnored() {
        assertThat(SearchText.parse("\"merkez bankası faiz"))
                .isEqualTo(new SearchText(List.of(), "merkez bankası faiz"));
    }

    @Test
    @DisplayName("boş tırnaklar ve fazla boşluklar atılır; aranacak bir şey kalmazsa ifade boştur")
    void emptyQuotesAndExtraSpacesAreRemoved() {
        assertThat(SearchText.parse("  \"  merkez   bankası \"   faiz  "))
                .isEqualTo(new SearchText(List.of("merkez bankası"), "faiz"));
        assertThat(SearchText.parse("\"\"").isEmpty()).isTrue();
        assertThat(SearchText.parse("deprem").isEmpty()).isFalse();
    }
}
