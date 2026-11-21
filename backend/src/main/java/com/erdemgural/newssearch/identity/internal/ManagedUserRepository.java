package com.erdemgural.newssearch.identity.internal;

import com.erdemgural.newssearch.identity.ManagedUser;
import com.erdemgural.newssearch.identity.UserFilter;
import com.erdemgural.newssearch.identity.UserRole;
import com.erdemgural.newssearch.identity.UserStatus;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/**
 * Yönetim panelinin {@code users} tablosu sorguları (FG-YP-01 – 03). Her istekte çalışan kimlik
 * eşleştirmesi ayrı sınıftadır ({@link UserRepository}).
 */
@Repository
class ManagedUserRepository {

    /**
     * Rol ve durum değişikliklerini sıraya sokan kilidin anahtarı (PostgreSQL danışma kilidi). Sayının
     * kendisinin anlamı yoktur; kullanıcı yönetimi dışında aynı sayıyı kullanan bir kilit yoktur.
     */
    private static final long USER_ADMINISTRATION_LOCK = 1_001L;

    private static final String COLUMNS = "id, email, display_name, role, status, created_at, version";

    /**
     * Filtreler: verilmeyen ({@code null}) filtre koşulu her satırda doğrudur. {@code CAST}: PostgreSQL,
     * yalnızca {@code IS NULL} ile karşılaştırılan bir parametrenin türünü kendisi çıkaramaz.
     *
     * <p>Arama {@code pg_c_utf8} kuralıyla küçük harfe çevrilerek yapılır: veritabanının varsayılan
     * {@code C} kuralı yalnızca ASCII harfleri çevirir ve "ŞAHİN" ile "şahin" eşleşmezdi.
     */
    private static final String FILTER = """
			WHERE (CAST(:status AS text) IS NULL OR status = :status)
			  AND (CAST(:role AS text) IS NULL OR role = :role)
			  AND (CAST(:pattern AS text) IS NULL
			       OR lower(email COLLATE pg_c_utf8) LIKE lower(CAST(:pattern AS text) COLLATE pg_c_utf8)
			       OR lower(display_name COLLATE pg_c_utf8) LIKE lower(CAST(:pattern AS text) COLLATE pg_c_utf8))
			""";

    private final JdbcClient jdbcClient;

    ManagedUserRepository(JdbcClient jdbcClient) {
        this.jdbcClient = jdbcClient;
    }

    /** Filtreye uyan kullanıcılardan bir sayfa; kayıt zamanına göre yeniden eskiye. */
    List<ManagedUser> findPage(UserFilter filter, int limit, long offset) {
        return withFilter(
                        jdbcClient.sql("SELECT " + COLUMNS + " FROM users " + FILTER
                                + " ORDER BY created_at DESC, id DESC LIMIT :limit OFFSET :offset"),
                        filter)
                .param("limit", limit)
                .param("offset", offset)
                .query(ManagedUserRepository::mapRow)
                .list();
    }

    long count(UserFilter filter) {
        return withFilter(jdbcClient.sql("SELECT count(*) FROM users " + FILTER), filter)
                .query(Long.class)
                .single();
    }

    /** Verilen kimliklerin e-postaları; bulunmayan kimlik sonuçta yer almaz. */
    Map<UUID, String> findEmails(Collection<UUID> userIds) {
        // Boş listeyle "IN ()" geçersiz SQL olurdu.
        if (userIds.isEmpty()) {
            return Map.of();
        }
        return jdbcClient
                .sql("SELECT id, email FROM users WHERE id IN (:userIds)")
                .param("userIds", userIds)
                .query((row, rowNumber) -> Map.entry(row.getObject("id", UUID.class), row.getString("email")))
                .list()
                .stream()
                .collect(Collectors.toUnmodifiableMap(Map.Entry::getKey, Map.Entry::getValue));
    }

    /**
     * Kullanıcıyı okur ve satırını işlem bitene kadar kilitler ({@code FOR UPDATE}): aynı kullanıcıyı aynı
     * anda değiştirmeye çalışan diğer istek bekler ve güncel hâlini görür.
     */
    Optional<ManagedUser> findForUpdate(UUID userId) {
        return jdbcClient
                .sql("SELECT " + COLUMNS + " FROM users WHERE id = :userId FOR UPDATE")
                .param("userId", userId)
                .query(ManagedUserRepository::mapRow)
                .optional();
    }

    /** Rolü ve durumu yazar, sürümü bir artırır; güncel kaydı döner. */
    ManagedUser update(UUID userId, UserRole role, UserStatus status) {
        return jdbcClient
                .sql("UPDATE users SET role = :role, status = :status, version = version + 1 WHERE id = :userId"
                        + " RETURNING " + COLUMNS)
                .param("userId", userId)
                .param("role", role.name())
                .param("status", status.name())
                .query(ManagedUserRepository::mapRow)
                .single();
    }

    /**
     * Rol ve durum değişikliklerini sıraya sokar; kilit işlem bitince kendiliğinden bırakılır.
     *
     * <p>Neden gerekli: iki yönetici aynı anda birbirinin rolünü düşürürse ikisi de "öbürü hâlâ aktif
     * yönetici" görür ve sistemde yönetici kalmaz (FG-YP-03). Kilitle ikinci istek birincinin bitmesini
     * bekler ve güncel sayıyı görür. Yalnızca kullanıcıların satırlarını kilitlemek yetmez: iki istek
     * satırları farklı sırada kilitleyip birbirini sonsuza kadar bekleyebilirdi (deadlock).
     */
    void lockAdministration() {
        jdbcClient
                .sql("SELECT pg_advisory_xact_lock(:key)")
                .param("key", USER_ADMINISTRATION_LOCK)
                .query()
                .singleRow();
    }

    long countActiveAdmins() {
        return jdbcClient
                .sql("SELECT count(*) FROM users WHERE role = 'ADMIN' AND status = 'ACTIVE'")
                .query(Long.class)
                .single();
    }

    private static JdbcClient.StatementSpec withFilter(JdbcClient.StatementSpec statement, UserFilter filter) {
        String status = filter.status() == null ? null : filter.status().name();
        String role = filter.role() == null ? null : filter.role().name();
        String pattern = filter.query() == null ? null : "%" + escapeLike(filter.query()) + "%";
        return statement.param("status", status).param("role", role).param("pattern", pattern);
    }

    /**
     * Aranan metindeki {@code %} ve {@code _} karakterleri LIKE'ta joker değil, harfin kendisi olarak
     * aranır. PostgreSQL'de LIKE'ın kaçış karakteri varsayılan olarak ters bölüdür.
     */
    private static String escapeLike(String text) {
        return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_");
    }

    private static ManagedUser mapRow(ResultSet row, int rowNumber) throws SQLException {
        return new ManagedUser(
                row.getObject("id", UUID.class),
                row.getString("email"),
                row.getString("display_name"),
                UserRole.valueOf(row.getString("role")),
                UserStatus.valueOf(row.getString("status")),
                row.getTimestamp("created_at").toInstant(),
                row.getInt("version"));
    }
}
