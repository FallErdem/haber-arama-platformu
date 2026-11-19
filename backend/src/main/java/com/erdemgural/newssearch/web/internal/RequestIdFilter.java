package com.erdemgural.newssearch.web.internal;

import com.erdemgural.newssearch.web.RequestIds;
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

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        String requestId = UUID.randomUUID().toString();
        MDC.put(RequestIds.LOG_FIELD_NAME, requestId);
        response.setHeader(RequestIds.HEADER_NAME, requestId);
        try {
            filterChain.doFilter(request, response);
        } finally {
            // İş parçacıkları yeniden kullanılır; kimlik bir sonraki isteğe taşınmamalı.
            MDC.remove(RequestIds.LOG_FIELD_NAME);
        }
    }
}
