package com.erdemgural.newssearch.audit.internal;

import com.erdemgural.newssearch.audit.AuditEvent;
import com.erdemgural.newssearch.audit.AuditLog;
import com.erdemgural.newssearch.web.RequestIds;
import org.springframework.stereotype.Service;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

/**
 * {@link AuditLog}'un uygulaması. İstek kimliği ve IP adresi şu anki istekten alınır; çağıranın bunları
 * taşıması gerekmez (FG-AL-02).
 *
 * <p>IP adresi: API, Traefik'in arkasındadır. Traefik, güvenmediği bir kaynaktan gelen {@code X-Forwarded-*}
 * başlıklarını siler ve kendi gördüğü adresi yazar; Tomcat bu başlığı yalnızca iç ağdaki bir vekilden
 * (Traefik'in pod adresi) gelirse kullanır ({@code server.forward-headers-strategy: native}). Böylece
 * istemcinin kendi gönderdiği başlığa güvenilmez (ADR-0016 6. bölüm).
 */
@Service
class AuditLogService implements AuditLog {

    private final AuditEventRepository repository;

    AuditLogService(AuditEventRepository repository) {
        this.repository = repository;
    }

    @Override
    public void record(AuditEvent event) {
        repository.insert(event, RequestIds.current(), currentIpAddress());
    }

    /** Bir HTTP isteği içinde değilse (örneğin zamanlanmış bir işte) {@code null}. */
    private static String currentIpAddress() {
        return RequestContextHolder.getRequestAttributes() instanceof ServletRequestAttributes attributes
                ? attributes.getRequest().getRemoteAddr()
                : null;
    }
}
