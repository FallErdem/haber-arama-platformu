package com.erdemgural.newssearch.web.internal;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.UUID;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Her isteğe bir kimlik verir; kimlik yanıtın {@code X-Request-Id} başlığına ve
 * o istek sırasında yazılan bütün log satırlarına eklenir (FOG-39). Kimlik her
 * zaman sunucuda üretilir; istemcinin gönderdiği değer kullanılmaz.
 */
@Component
// Güvenlik filtresinden önce çalışmalı ki 401 ve 403 yanıtları da kimlik taşısın.
@Order(Ordered.HIGHEST_PRECEDENCE)
class RequestIdFilter extends OncePerRequestFilter {

    static final String HEADER_NAME = "X-Request-Id";
    static final String LOG_FIELD_NAME = "requestId";

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        String requestId = UUID.randomUUID().toString();
        MDC.put(LOG_FIELD_NAME, requestId);
        response.setHeader(HEADER_NAME, requestId);
        try {
            filterChain.doFilter(request, response);
        } finally {
            // İş parçacıkları yeniden kullanılır; kimlik bir sonraki isteğe taşınmamalı.
            MDC.remove(LOG_FIELD_NAME);
        }
    }
}
