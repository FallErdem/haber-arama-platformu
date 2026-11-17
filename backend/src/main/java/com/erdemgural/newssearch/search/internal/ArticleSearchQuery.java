package com.erdemgural.newssearch.search.internal;

import co.elastic.clients.elasticsearch._types.FieldValue;
import co.elastic.clients.elasticsearch._types.SortOptions;
import co.elastic.clients.elasticsearch._types.SortOrder;
import co.elastic.clients.elasticsearch._types.query_dsl.BoolQuery;
import co.elastic.clients.elasticsearch._types.query_dsl.Operator;
import co.elastic.clients.elasticsearch._types.query_dsl.Query;
import co.elastic.clients.elasticsearch._types.query_dsl.TextQueryType;
import co.elastic.clients.elasticsearch.core.SearchRequest;
import co.elastic.clients.elasticsearch.core.search.HighlightField;
import co.elastic.clients.elasticsearch.core.search.HighlighterEncoder;
import co.elastic.clients.util.NamedValue;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Arama isteğini Elasticsearch sorgusuna çevirir (API sözleşmesi 4.1). Kurallar ve bunların
 * gerçek haberlerle denenmesi {@code docs/05-veri-modeli.md} 5.5 bölümündedir.
 */
final class ArticleSearchQuery {

    /** Aramaların yapıldığı takma ad; etkin neslin bütün aylık indekslerini kapsar. */
    static final String ALIAS = "articles";

    static final String PUBLISHED_AT = "published_at";

    /**
     * Alan ağırlıkları (FG-AR-01): başlıktaki eşleşme en yüksek, içerikteki en düşük. {@code ^3},
     * o alandaki eşleşmenin puanını üçle çarpar. Türkçe ve İngilizce alanlar birlikte aranır;
     * her haber yalnızca kendi dilinin alanlarını taşır.
     */
    static final List<String> MAIN_FIELDS =
            List.of("title_tr^3", "summary_tr^2", "content_tr", "title_en^3", "summary_en^2", "content_en");

    /**
     * Türkçe alanların katlanmış alt alanları: Türkçe karaktersiz yazılan sorguları ve yerleşik
     * kök bulucunun kaçırdığı çoğulları yakalar (ADR-0017, 11. bölüm).
     */
    static final List<String> FOLDED_FIELDS = List.of("title_tr.folded^3", "summary_tr.folded^2", "content_tr.folded");

    /**
     * Katlanmış alanlar kaba eşleşir (cumhurbaşkanı / cumhuriyet); düşük ağırlıkla katılırlar ki
     * asıl alanda eşleşen haberler üstte kalsın.
     */
    static final float FOLDED_BOOST = 0.2f;

    /**
     * Kaç kelimenin geçmesi gerektiği: 1 veya 2 kelimede hepsi, daha fazlasında dörtte üçü
     * (3 kelimede 2, 4 kelimede 3). "Hepsi" uzun sorgularda tek kelime tutmayınca sonuçsuz
     * bırakıyor, "biri yeter" ilgisiz sonuç getiriyordu.
     */
    static final String MINIMUM_SHOULD_MATCH = "2<75%";

    /**
     * Kelimeleri yan yana ve aynı sırada içeren habere eklenen puanın ağırlığı. "merkez bankası
     * faiz" aramasında "Merkez Bankası faiz kararı" başlığı, kelimeleri dağınık geçen haberlerin
     * önüne geçer. Kümedeki haberlerle denendi: 1 yetmedi, 3 fark yaratmadı (veri modeli 5.5).
     */
    static final float PHRASE_BOOST = 2f;

    /** 1 yıldan eski (soğuk) haberlerin ilgililik puanı bu oranla çarpılır (ADR-0011). */
    static final double COLD_BOOST = 0.5;

    static final String COLD_BEFORE = "now-1y";

    /** Vurgulanan alanlar; katlanmış alt alan, eşleşme yalnızca orada olduğunda kullanılır. */
    static final List<String> HIGHLIGHT_FIELDS =
            List.of("title_tr", "title_en", "title_tr.folded", "summary_tr", "summary_en", "summary_tr.folded");

    static final String HIGHLIGHT_START = "<mark>";
    static final String HIGHLIGHT_END = "</mark>";

    private ArticleSearchQuery() {}

    /**
     * @param categoryWindows süreli kategoriler ve süreleri (Son Dakika: 6 saat)
     */
    static SearchRequest build(SearchCriteria criteria, Map<String, Duration> categoryWindows) {
        BoolQuery.Builder bool = new BoolQuery.Builder();
        if (criteria.hasQuery()) {
            SearchText text = SearchText.parse(criteria.query());
            // Yalnızca tırnak işaretinden oluşan bir ifadede aranacak kelime yoktur; bütün haberler döner.
            if (!text.isEmpty()) {
                bool.must(textQuery(text));
            }
        }
        // filter: eşleşmeyi daraltır ama puanı etkilemez.
        bool.filter(filters(criteria, categoryWindows));
        Query query = bool.build()._toQuery();

        SearchRequest.Builder request = new SearchRequest.Builder()
                .index(ALIAS)
                // Henüz hiç haber aktarılmamışsa takma ad da yoktur; hata yerine boş sonuç dönsün.
                .ignoreUnavailable(true)
                .allowNoIndices(true)
                .query(query)
                .from(criteria.page() * criteria.size())
                .size(criteria.size())
                // Belgenin kendisi istenmez; gösterilecek bilgiler PostgreSQL'den okunur.
                .source(source -> source.fetch(false))
                // Toplam sayı en fazla 10.000'e kadar sayılır (sözleşme 2.4).
                .trackTotalHits(total -> total.count(SearchCriteria.MAX_RESULT_WINDOW))
                .sort(sort(criteria.sort()));
        if (criteria.hasQuery()) {
            request.highlight(highlight -> highlight
                    .preTags(HIGHLIGHT_START)
                    .postTags(HIGHLIGHT_END)
                    // html: metindeki <, > ve & karakterleri kaçış koduna çevrilir; yanıttaki tek
                    // gerçek etiket bizim eklediğimiz <mark> olur (kaynak metinden etiket sızamaz).
                    .encoder(HighlighterEncoder.Html)
                    // 0: alan parçalara bölünmez, tamamı vurgularıyla birlikte döner.
                    .numberOfFragments(0)
                    .fields(HIGHLIGHT_FIELDS.stream()
                            .map(field -> NamedValue.of(field, HighlightField.of(options -> options)))
                            .toList()));
        }
        return request.build();
    }

    /**
     * Arama ifadesinin sorgusu. Soğuk haberlerin puanı düşürülür ama sonuçtan çıkarılmazlar.
     *
     * <ul>
     *   <li>Tırnak dışındaki kelimeler iki biçimde aranır: asıl alanlarda (dil analizörüyle) ve düşük
     *       ağırlıkla katlanmış alanlarda; haberin birinde eşleşmesi yeterlidir. Kelimeleri yan yana ve
     *       aynı sırada içeren habere ayrıca puan eklenir; bu eşleşme zorunlu değildir.
     *   <li>Tırnak içindeki her öbek zorunludur: haberde kelimeleri yan yana ve aynı sırada geçmelidir.
     *       Türkçe karaktersiz yazılmış öbek de katlanmış alanlarda aranır.
     * </ul>
     */
    private static Query textQuery(SearchText text) {
        BoolQuery.Builder matches = new BoolQuery.Builder();
        if (!text.words().isEmpty()) {
            matches.must(must -> must.bool(words -> words.should(multiMatch(text.words(), MAIN_FIELDS, 1f))
                    .should(multiMatch(text.words(), FOLDED_FIELDS, FOLDED_BOOST))
                    .minimumShouldMatch("1")));
            matches.should(phrase(text.words(), MAIN_FIELDS, PHRASE_BOOST));
        }
        for (String phrase : text.phrases()) {
            matches.must(must -> must.bool(exact -> exact.should(phrase(phrase, MAIN_FIELDS, PHRASE_BOOST))
                    .should(phrase(phrase, FOLDED_FIELDS, FOLDED_BOOST))
                    .minimumShouldMatch("1")));
        }
        Query positive = matches.build()._toQuery();
        return Query.of(query -> query.boosting(boosting -> boosting.positive(positive)
                .negative(negative -> negative.range(
                        range -> range.date(date -> date.field(PUBLISHED_AT).lt(COLD_BEFORE))))
                .negativeBoost(COLD_BOOST)));
    }

    /**
     * Kelime öbeği: kelimeler, dil analizöründen geçtikten sonra yan yana ve aynı sırada olmalıdır.
     * Ekler kök bulucu tarafından atıldığı için "merkez bankası" öbeği "Merkez Bankası'nın" ile de
     * eşleşir.
     */
    private static Query phrase(String text, List<String> fields, float boost) {
        return Query.of(query -> query.multiMatch(match ->
                match.query(text).fields(fields).type(TextQueryType.Phrase).boost(boost)));
    }

    /**
     * cross_fields: alanlar tek bir büyük alan gibi değerlendirilir; "galatasaray" başlıkta,
     * "fenerbahçe" içerikte geçen haber de eşleşir.
     */
    private static Query multiMatch(String text, List<String> fields, float boost) {
        return Query.of(query -> query.multiMatch(match -> match.query(text)
                .fields(fields)
                .type(TextQueryType.CrossFields)
                .operator(Operator.Or)
                .minimumShouldMatch(MINIMUM_SHOULD_MATCH)
                .boost(boost)));
    }

    private static List<Query> filters(SearchCriteria criteria, Map<String, Duration> categoryWindows) {
        List<Query> filters = new ArrayList<>();
        if (!criteria.sources().isEmpty()) {
            filters.add(anyOf("source_code", criteria.sources()));
        }
        if (criteria.language() != null) {
            filters.add(
                    Query.of(query -> query.term(term -> term.field("language").value(criteria.language()))));
        }
        if (!criteria.categories().isEmpty()) {
            filters.add(categoryFilter(criteria.categories(), categoryWindows));
        }
        if (criteria.from() != null || criteria.to() != null) {
            filters.add(Query.of(query -> query.range(range -> range.date(date -> {
                date.field(PUBLISHED_AT);
                if (criteria.from() != null) {
                    date.gte(criteria.from().toString());
                }
                if (criteria.to() != null) {
                    date.lte(criteria.to().toString());
                }
                return date;
            }))));
        }
        return filters;
    }

    /**
     * Seçilen kategorilerden herhangi birini taşıyan haberler. Süreli bir kategori (Son Dakika)
     * yalnızca süresi içinde yayımlanmış haberlerde sayılır (FG-AR-12): altı saatten eski bir
     * haber Son Dakika filtresinde çıkmaz, ama konu kategorisinde çıkmaya devam eder.
     */
    private static Query categoryFilter(List<String> categories, Map<String, Duration> categoryWindows) {
        BoolQuery.Builder anyCategory = new BoolQuery.Builder().minimumShouldMatch("1");
        List<String> plainCategories = categories.stream()
                .filter(code -> !categoryWindows.containsKey(code))
                .toList();
        if (!plainCategories.isEmpty()) {
            anyCategory.should(anyOf("categories", plainCategories));
        }
        for (String code : categories) {
            Duration window = categoryWindows.get(code);
            if (window != null) {
                // now-6h: süre Elasticsearch'in kendi saatine göre hesaplanır.
                String since = "now-" + window.toHours() + "h";
                anyCategory.should(should -> should.bool(windowed -> windowed.filter(filter ->
                                filter.term(term -> term.field("categories").value(code)))
                        .filter(filter -> filter.range(range ->
                                range.date(date -> date.field(PUBLISHED_AT).gte(since))))));
            }
        }
        return anyCategory.build()._toQuery();
    }

    private static Query anyOf(String field, List<String> values) {
        return Query.of(query -> query.terms(terms -> terms.field(field)
                .terms(list -> list.value(values.stream().map(FieldValue::of).toList()))));
    }

    private static List<SortOptions> sort(SearchSort sort) {
        SortOptions newestFirst = SortOptions.of(
                options -> options.field(field -> field.field(PUBLISHED_AT).order(SortOrder.Desc)));
        if (sort == SearchSort.NEWEST) {
            return List.of(newestFirst);
        }
        // Puanı eşit olan haberlerde yeni olan önce gelir.
        return List.of(SortOptions.of(options -> options.score(score -> score.order(SortOrder.Desc))), newestFirst);
    }
}
