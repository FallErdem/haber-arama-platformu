package com.erdemgural.newssearch.web;

import java.util.List;

/**
 * İstekteki bir veya birden fazla alan geçersiz. {@code 400 VALIDATION_FAILED} yanıtına ve
 * yanıttaki {@code errors} listesine çevrilir (API sözleşmesi 2.6).
 */
public class InvalidRequestException extends RuntimeException {

    private final transient List<FieldError> errors;

    public InvalidRequestException(List<FieldError> errors) {
        super("Geçersiz istek: " + errors);
        this.errors = List.copyOf(errors);
    }

    public List<FieldError> errors() {
        return errors;
    }
}
