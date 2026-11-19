package com.erdemgural.newssearch.web;

import org.slf4j.MDC;

/**
 * İsteğin kimliği (API sözleşmesi 2.7). Kimliği istek filtresi üretir ve isteğin log bağlamına (MDC)
 * koyar; audit kayıtları da aynı kimliği buradan okur, böylece bir audit kaydı loglardaki satırlarla
 * eşleştirilebilir (FG-AL-02).
 */
public final class RequestIds {

    public static final String HEADER_NAME = "X-Request-Id";
    public static final String LOG_FIELD_NAME = "requestId";

    private RequestIds() {}

    /** Şu anki isteğin kimliği; bir istek dışında (örneğin açılışta) {@code null}. */
    public static String current() {
        return MDC.get(LOG_FIELD_NAME);
    }
}
