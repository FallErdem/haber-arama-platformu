package com.erdemgural.newssearch.audit.internal;

import com.erdemgural.newssearch.audit.AuditEvent;
import com.erdemgural.newssearch.audit.AuditEventFilter;
import com.erdemgural.newssearch.audit.AuditRecord;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

/**
 * {@code audit_events} tablosu (veri modeli 3.13). Yalnızca ekleme ve okuma vardır: {@code news_app}'in bu
 * tabloda güncelleme ve silme yetkisi yoktur, olsaydı da tetikleyici reddederdi (V8, V9).
 */
@Repository
class AuditEventRepository {

    private static final String SELECT = """
			SELECT id, occurred_at, actor_type, actor_user_id, action, target_type, target_id, result,
			       request_id, host(ip_address) AS ip_address, details::text AS details
			FROM audit_events
			""";

    /**
     * Filtreler: verilmeyen ({@code null}) filtre koşulu her satırda doğrudur. {@code CAST}: PostgreSQL,
     * yalnızca {@code IS NULL} ile karşılaştırılan bir parametrenin türünü kendisi çıkaramaz. Alt sınır
     * ({@code from}) her zaman verilir; PostgreSQL yalnızca aralığa düşen aylık bölümlere bakar.
     */
    private static final String FILTER = """
			WHERE occurred_at >= :from
			  AND (CAST(:to AS timestamptz) IS NULL OR occurred_at <= :to)
			  AND (CAST(:actorUserId AS uuid) IS NULL OR actor_user_id = :actorUserId)
			  AND (CAST(:action AS text) IS NULL OR action = :action)
			  AND (CAST(:targetType AS text) IS NULL OR target_type = :targetType)
			  AND (CAST(:targetId AS uuid) IS NULL OR target_id = :targetId)
			  AND (CAST(:result AS text) IS NULL OR result = :result)
			""";

    /** Aynı anda yazılan kayıtların sırası kimlikle sabitlenir; yoksa sayfalar arasında bir kayıt kayabilirdi. */
    private static final String ORDER = " ORDER BY occurred_at DESC, id DESC";

    private static final TypeReference<Map<String, Object>> DETAILS_TYPE = new TypeReference<>() {};

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

    /** Filtreye uyan kayıtlardan bir sayfa, yeniden eskiye. */
    List<AuditRecord> findPage(AuditEventFilter filter, int limit, long offset) {
        return withFilter(jdbcClient.sql(SELECT + FILTER + ORDER + " LIMIT :limit OFFSET :offset"), filter)
                .param("limit", limit)
                .param("offset", offset)
                .query(this::mapRow)
                .list();
    }

    long count(AuditEventFilter filter) {
        return withFilter(jdbcClient.sql("SELECT count(*) FROM audit_events " + FILTER), filter)
                .query(Long.class)
                .single();
    }

    /**
     * Sıralamada {@code after}'dan sonra gelen (ondan daha eski) kayıtlar; {@code after} {@code null} ise
     * baştan. "Son görülen kayıttan sonrası" diye sorulur (keyset pagination): {@code OFFSET} gibi atlanan
     * satırları baştan saymadığı için 100.000. kayda gelindiğinde de ilk parça kadar hızlıdır.
     */
    List<AuditRecord> findChunkAfter(AuditEventFilter filter, AuditRecord after, int limit) {
        Timestamp afterOccurredAt = after == null ? null : Timestamp.from(after.occurredAt());
        UUID afterId = after == null ? null : after.id();
        return withFilter(jdbcClient.sql(SELECT + FILTER + """
						  AND (CAST(:afterOccurredAt AS timestamptz) IS NULL
						       OR (occurred_at, id) < (CAST(:afterOccurredAt AS timestamptz), CAST(:afterId AS uuid)))
						""" + ORDER + " LIMIT :limit"), filter)
                .param("afterOccurredAt", afterOccurredAt)
                .param("afterId", afterId)
                .param("limit", limit)
                .query(this::mapRow)
                .list();
    }

    private static JdbcClient.StatementSpec withFilter(JdbcClient.StatementSpec statement, AuditEventFilter filter) {
        // Zaman parametreleri, projedeki diğer sorgulardaki gibi Timestamp olarak verilir.
        Timestamp to = filter.to() == null ? null : Timestamp.from(filter.to());
        return statement
                .param("from", Timestamp.from(filter.from()))
                .param("to", to)
                .param("actorUserId", filter.actorUserId())
                .param("action", filter.action())
                .param("targetType", filter.targetType())
                .param("targetId", filter.targetId())
                .param("result", filter.result());
    }

    private AuditRecord mapRow(ResultSet row, int rowNumber) throws SQLException {
        String details = row.getString("details");
        return new AuditRecord(
                row.getObject("id", UUID.class),
                instant(row, "occurred_at"),
                row.getString("actor_type"),
                row.getObject("actor_user_id", UUID.class),
                row.getString("action"),
                row.getString("target_type"),
                row.getObject("target_id", UUID.class),
                row.getString("result"),
                row.getString("request_id"),
                row.getString("ip_address"),
                details == null ? Map.of() : jsonMapper.readValue(details, DETAILS_TYPE));
    }

    private static Instant instant(ResultSet row, String column) throws SQLException {
        Timestamp timestamp = row.getTimestamp(column);
        return timestamp == null ? null : timestamp.toInstant();
    }
}
