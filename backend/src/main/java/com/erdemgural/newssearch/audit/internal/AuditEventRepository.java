package com.erdemgural.newssearch.audit.internal;

import com.erdemgural.newssearch.audit.AuditEvent;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
import tools.jackson.databind.json.JsonMapper;

/**
 * {@code audit_events} tablosu (veri modeli 3.13). Yalnızca ekleme vardır: {@code news_app}'in bu tabloda
 * güncelleme ve silme yetkisi yoktur, olsaydı da tetikleyici reddederdi (V8, V9).
 */
@Repository
class AuditEventRepository {

    private final JdbcClient jdbcClient;
    private final JsonMapper jsonMapper;

    AuditEventRepository(JdbcClient jdbcClient, JsonMapper jsonMapper) {
        this.jdbcClient = jdbcClient;
        this.jsonMapper = jsonMapper;
    }

    /**
     * Kaydı ekler. {@code occurred_at} veritabanının saatiyle ({@code now()}, UTC olarak saklanır)
     * dolar. API'nin yazdığı her kaydı bir kullanıcı yapar; sistem kayıtlarını işçi yazar.
     *
     * @param ipAddress isteğin geldiği adres; {@code inet} türüne veritabanında çevrilir
     */
    void insert(AuditEvent event, String requestId, String ipAddress) {
        String targetType =
                event.targetType() == null ? null : event.targetType().name();
        // Ayrıntısı olmayan işlemde sütun boş kalır; "{}" yazılmaz.
        String details = event.details().isEmpty() ? null : jsonMapper.writeValueAsString(event.details());
        jdbcClient
                .sql("""
				INSERT INTO audit_events (
				    actor_type, actor_user_id, action, target_type, target_id,
				    result, request_id, ip_address, details)
				VALUES (
				    'USER', :actorUserId, :action, :targetType, :targetId,
				    :result, :requestId, CAST(:ipAddress AS inet), CAST(:details AS jsonb))
				""")
                .param("actorUserId", event.actorUserId())
                .param("action", event.action().name())
                .param("targetType", targetType)
                .param("targetId", event.targetId())
                .param("result", event.success() ? "SUCCESS" : "FAILURE")
                .param("requestId", requestId)
                .param("ipAddress", ipAddress)
                .param("details", details)
                .update();
    }
}
