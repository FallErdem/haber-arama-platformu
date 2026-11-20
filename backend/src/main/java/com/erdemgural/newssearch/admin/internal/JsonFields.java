package com.erdemgural.newssearch.admin.internal;

import com.erdemgural.newssearch.web.FieldError;
import com.erdemgural.newssearch.web.FieldError.Code;
import com.erdemgural.newssearch.web.InvalidRequestException;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import tools.jackson.databind.JsonNode;

/**
 * İstek gövdesindeki alanların okunması ve doğrulanması. Gövde bir Java kaydına bağlanmak yerine JSON ağacı
 * ({@link JsonNode}) olarak okunur, iki nedenle:
 *
 * <ul>
 *   <li>PATCH'te "alan gönderilmedi" (değişmez) ile "alan {@code null} gönderildi" (boşaltılsın) ayırt
 *       edilebilsin (sözleşme 2.5). Bir kayda bağlanınca ikisi de {@code null} olurdu.
 *   <li>Yanlış türdeki bir değer (sayı yerine metin) de diğer hatalarla birlikte, alan adı ve koduyla
 *       bildirilsin (sözleşme 2.6).
 * </ul>
 *
 * Hatalar toplanır; {@link #throwIfInvalid()} hepsini tek yanıtta bildirir.
 */
final class JsonFields {

    private final JsonNode body;
    private final List<FieldError> errors = new ArrayList<>();

    JsonFields(JsonNode body) {
        this.body = body;
    }

    boolean has(String name) {
        return body != null && body.has(name);
    }

    /** Gönderilmesi zorunlu, boş olamayan metin. Eksik veya geçersizse {@code null} döner ve hata eklenir. */
    String requiredText(String name, int maxLength) {
        if (!has(name) || body.get(name).isNull()) {
            return addError(name, Code.INVALID_VALUE);
        }
        return text(name, maxLength);
    }

    /** Boş olamayan metin; gönderilmediyse {@code null} (değişmez). Açıkça {@code null} gönderilemez. */
    String text(String name, int maxLength) {
        if (!has(name)) {
            return null;
        }
        JsonNode value = body.get(name);
        if (!value.isString() || value.stringValue().isBlank()) {
            return addError(name, Code.INVALID_VALUE);
        }
        String text = value.stringValue().strip();
        if (text.length() > maxLength) {
            return addError(name, Code.MAX_LENGTH);
        }
        return text;
    }

    /**
     * Boş bırakılabilen metin: gönderilmediyse {@code null} (değişmez), {@code null} veya boş metin
     * gönderildiyse {@code Optional.empty()} (boşaltılır), değer varsa o değer.
     */
    Optional<String> nullableText(String name, int maxLength) {
        if (!has(name)) {
            return null;
        }
        JsonNode value = body.get(name);
        if (value.isNull() || (value.isString() && value.stringValue().isBlank())) {
            return Optional.empty();
        }
        String text = text(name, maxLength);
        return text == null ? Optional.empty() : Optional.of(text);
    }

    /** Eklemede isteğe bağlı metin: gönderilmediyse, {@code null} veya boşsa {@code null}. */
    String optionalText(String name, int maxLength) {
        Optional<String> value = nullableText(name, maxLength);
        return value == null ? null : value.orElse(null);
    }

    /** Gönderilmesi zorunlu tam sayı. */
    Integer requiredInteger(String name, int min, int max) {
        if (!has(name) || body.get(name).isNull()) {
            return addError(name, Code.INVALID_VALUE);
        }
        return integer(name, min, max);
    }

    /** Tam sayı; gönderilmediyse {@code null} (değişmez). Açıkça {@code null} gönderilemez. */
    Integer integer(String name, int min, int max) {
        if (!has(name)) {
            return null;
        }
        JsonNode value = body.get(name);
        if (!value.isIntegralNumber() || !value.canConvertToInt()) {
            return addError(name, Code.INVALID_VALUE);
        }
        int number = value.intValue();
        if (number < min) {
            return addError(name, Code.MIN_VALUE);
        }
        if (number > max) {
            return addError(name, Code.MAX_VALUE);
        }
        return number;
    }

    /** Boş bırakılabilen tam sayı; anlamı {@link #nullableText} ile aynı. */
    Optional<Integer> nullableInteger(String name, int min, int max) {
        if (!has(name)) {
            return null;
        }
        if (body.get(name).isNull()) {
            return Optional.empty();
        }
        Integer number = integer(name, min, max);
        return number == null ? Optional.empty() : Optional.of(number);
    }

    /** Eklemede isteğe bağlı tam sayı: gönderilmediyse veya {@code null} ise {@code null}. */
    Integer optionalInteger(String name, int min, int max) {
        Optional<Integer> value = nullableInteger(name, min, max);
        return value == null ? null : value.orElse(null);
    }

    /** Doğru/yanlış; gönderilmediyse {@code null} (değişmez). */
    Boolean bool(String name) {
        if (!has(name)) {
            return null;
        }
        JsonNode value = body.get(name);
        if (!value.isBoolean()) {
            return addError(name, Code.INVALID_VALUE);
        }
        return value.booleanValue();
    }

    Boolean requiredBool(String name) {
        if (!has(name)) {
            return addError(name, Code.INVALID_VALUE);
        }
        return bool(name);
    }

    /** Değer verilmişse izin verilen değerlerden biri mi; değilse hata ekler. */
    void requireOneOf(String name, String value, List<String> allowed) {
        if (value != null && !allowed.contains(value)) {
            addError(name, Code.INVALID_VALUE);
        }
    }

    /** Değer verilmişse mutlak bir {@code http} veya {@code https} adresi mi; değilse hata ekler. */
    void requireHttpUrl(String name, String value) {
        if (value != null && !isHttpUrl(value)) {
            addError(name, Code.INVALID_VALUE);
        }
    }

    <T> T addError(String name, Code code) {
        errors.add(new FieldError(name, code));
        return null;
    }

    void throwIfInvalid() {
        if (!errors.isEmpty()) {
            throw new InvalidRequestException(errors);
        }
    }

    private static boolean isHttpUrl(String value) {
        try {
            URI uri = new URI(value);
            return ("http".equals(uri.getScheme()) || "https".equals(uri.getScheme())) && uri.getHost() != null;
        } catch (URISyntaxException exception) {
            return false;
        }
    }
}
