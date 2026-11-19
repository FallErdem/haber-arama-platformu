package com.erdemgural.newssearch.search.internal;

import com.erdemgural.newssearch.web.ApiException;
import com.erdemgural.newssearch.web.ErrorCode;
import com.erdemgural.newssearch.web.FieldError;
import com.erdemgural.newssearch.web.FieldError.Code;
import com.erdemgural.newssearch.web.InvalidRequestException;
import com.erdemgural.newssearch.web.PageParameters;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import org.springframework.http.HttpStatus;

/**
 * Doğrulanmış arama isteği (API sözleşmesi 4.1). Adres parametreleri metin olarak gelir; burada
 * okunur, sınırları denetlenir ve varsayılan değerleri verilir. Bu sınıfın bir örneği varsa
 * içindeki değerler geçerlidir; sorguyu kuran kod yeniden denetlemez.
 *
 * @param query arama ifadesi; verilmediyse veya boşsa {@code null}
 * @param from yayın tarihi alt sınırı (dahil); yoksa {@code null}
 * @param to yayın tarihi üst sınırı (dahil); yoksa {@code null}
 */
record SearchCriteria(
        String query,
        List<String> sources,
        String language,
        List<String> categories,
        Instant from,
        Instant to,
        SearchSort sort,
        int page,
        int size) {

    static final int MAX_QUERY_LENGTH = 200;

    /**
     * Elasticsearch varsayılan olarak ilk 10.000 sonucun ötesine sayfalamaz (her sayfa için
     * baştan o noktaya kadar bütün sonuçları sıralaması gerekir). Sınır burada da uygulanır.
     */
    static final int MAX_RESULT_WINDOW = 10_000;

    private static final List<String> LANGUAGES = List.of("tr", "en");

    boolean hasQuery() {
        return query != null;
    }

    /**
     * Parametreleri okur. Geçersiz alan varsa hepsini birlikte bildiren {@link
     * InvalidRequestException}, sayfa sınırı aşılıyorsa {@code PAGE_LIMIT_EXCEEDED} fırlatır.
     */
    static SearchCriteria parse(
            String q,
            String sources,
            String language,
            String categories,
            String from,
            String to,
            String sort,
            String page,
            String size) {
        List<FieldError> errors = new ArrayList<>();

        String query = blankToNull(q);
        if (query != null && query.length() > MAX_QUERY_LENGTH) {
            errors.add(new FieldError("q", Code.MAX_LENGTH));
        }

        String chosenLanguage = blankToNull(language);
        if (chosenLanguage != null && !LANGUAGES.contains(chosenLanguage)) {
            errors.add(new FieldError("language", Code.INVALID_VALUE));
        }

        Instant fromInstant = parseInstant("from", from, errors);
        Instant toInstant = parseInstant("to", to, errors);
        if (fromInstant != null && toInstant != null && fromInstant.isAfter(toInstant)) {
            errors.add(new FieldError("from", Code.INVALID_RANGE));
        }

        SearchSort chosenSort = parseSort(sort, errors);
        PageParameters pageParameters = PageParameters.parse(page, size, errors);
        int pageNumber = pageParameters.page();
        int pageSize = pageParameters.size();

        if (!errors.isEmpty()) {
            throw new InvalidRequestException(errors);
        }
        // long: çok büyük bir sayfa numarasında çarpım taşmasın.
        if ((pageNumber + 1L) * pageSize > MAX_RESULT_WINDOW) {
            throw new ApiException(HttpStatus.BAD_REQUEST, ErrorCode.PAGE_LIMIT_EXCEEDED);
        }

        // Arama ifadesi yoksa ilgililik hesaplanamaz; haberler tarihe göre listelenir.
        SearchSort effectiveSort = query == null ? SearchSort.NEWEST : chosenSort;
        return new SearchCriteria(
                query,
                splitCodes(sources),
                chosenLanguage,
                splitCodes(categories),
                fromInstant,
                toInstant,
                effectiveSort,
                pageNumber,
                pageSize);
    }

    private static String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.strip();
    }

    /** Virgülle ayrılmış kodlar: {@code "TRT, NYT"} -> {@code [TRT, NYT]}. */
    private static List<String> splitCodes(String value) {
        if (value == null) {
            return List.of();
        }
        return Arrays.stream(value.split(","))
                .map(String::strip)
                .filter(code -> !code.isEmpty())
                .distinct()
                .toList();
    }

    private static Instant parseInstant(String field, String value, List<FieldError> errors) {
        String text = blankToNull(value);
        if (text == null) {
            return null;
        }
        try {
            // ISO 8601, UTC (sözleşme 2.3): 2026-11-05T09:30:00Z
            return Instant.parse(text);
        } catch (DateTimeParseException exception) {
            errors.add(new FieldError(field, Code.INVALID_VALUE));
            return null;
        }
    }

    private static SearchSort parseSort(String value, List<FieldError> errors) {
        String text = blankToNull(value);
        if (text == null || text.equals("relevance")) {
            return SearchSort.RELEVANCE;
        }
        if (text.equals("newest")) {
            return SearchSort.NEWEST;
        }
        errors.add(new FieldError("sort", Code.INVALID_VALUE));
        return SearchSort.RELEVANCE;
    }
}
