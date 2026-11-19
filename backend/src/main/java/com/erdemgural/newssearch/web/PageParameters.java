package com.erdemgural.newssearch.web;

import java.util.List;

/**
 * Sayfalı listelerin {@code page} ve {@code size} parametreleri (API sözleşmesi 2.4): {@code page}
 * 0'dan başlar; {@code size} varsayılan olarak 20, en fazla 100'dür. Bütün sayfalı uç noktalar aynı
 * kuralı bu sınıfla uygular.
 */
public record PageParameters(int page, int size) {

    public static final int DEFAULT_SIZE = 20;
    public static final int MAX_SIZE = 100;

    /**
     * Adres parametrelerini okur. Hatalar fırlatılmaz, {@code errors} listesine eklenir: çağıran, isteğin
     * diğer alanlarındaki hatalarla birlikte hepsini tek yanıtta bildirir (sözleşme 2.6). Geçersiz bir
     * değerin yerine varsayılan döner; liste boş değilse çağıran bu sonucu kullanmamalıdır.
     */
    public static PageParameters parse(String page, String size, List<FieldError> errors) {
        int pageNumber = parseInteger("page", page, 0, 0, Integer.MAX_VALUE, errors);
        int pageSize = parseInteger("size", size, DEFAULT_SIZE, 1, MAX_SIZE, errors);
        return new PageParameters(pageNumber, pageSize);
    }

    /** Sayfanın ilk öğesinin sırası (SQL'deki {@code OFFSET}). {@code long}: çarpım taşmasın. */
    public long offset() {
        return (long) page * size;
    }

    private static int parseInteger(
            String field, String value, int defaultValue, int min, int max, List<FieldError> errors) {
        if (value == null || value.isBlank()) {
            return defaultValue;
        }
        int number;
        try {
            number = Integer.parseInt(value.strip());
        } catch (NumberFormatException exception) {
            errors.add(new FieldError(field, FieldError.Code.INVALID_VALUE));
            return defaultValue;
        }
        if (number < min) {
            errors.add(new FieldError(field, FieldError.Code.MIN_VALUE));
            return defaultValue;
        }
        if (number > max) {
            errors.add(new FieldError(field, FieldError.Code.MAX_VALUE));
            return defaultValue;
        }
        return number;
    }
}
