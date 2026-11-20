package com.erdemgural.newssearch.audit;

/**
 * API'nin yazdığı audit işlem kodları ({@code audit_events.action}; veri modeli 3.13). İşçinin yazdığı
 * sistem kayıtlarının kodları (örneğin {@code FEED_AUTO_DISABLED}) işçidedir. Yeni bir denetlenen işlem
 * (FG-AL-01) buraya kendi koduyla eklenir.
 */
public enum AuditAction {
    /** Kullanıcının ilk isteğinde kaydı oluşturuldu (ADR-0014). */
    USER_REGISTERED,
    /** Token'daki oturum kimliği ({@code sid}) kullanıcının son oturumundan farklı: yeni oturum. */
    SESSION_STARTED,
    /** Kimliği doğrulanmış kullanıcının isteği reddedildi (403). */
    ACCESS_DENIED,
    /** Yönetici onay bekleyen kullanıcıyı onayladı (FG-YP-01). */
    USER_APPROVED,
    /** Yönetici onay bekleyen kullanıcıyı reddetti (FG-YP-01). */
    USER_REJECTED,
    /** Yönetici kullanıcının rolünü değiştirdi (FG-YP-02). */
    USER_ROLE_CHANGED,
    /** Yönetici kullanıcıyı aktif veya pasif yaptı (FG-YP-02). */
    USER_STATUS_CHANGED,
    /** Yönetici kaynak ekledi (FG-YP-04). */
    SOURCE_CREATED,
    /** Yönetici kaynağın ayarlarını değiştirdi. */
    SOURCE_UPDATED,
    /** Yönetici kaynağı etkinleştirdi. */
    SOURCE_ENABLED,
    /** Yönetici kaynağı devre dışı bıraktı. */
    SOURCE_DISABLED,
    /** Yönetici kaynak için toplamayı elle başlattı (FG-YP-08). */
    FETCH_REQUESTED,
    /** Yönetici kaynağa besleme ekledi (FG-YP-04). */
    FEED_CREATED,
    /** Yönetici beslemenin ayarlarını değiştirdi. */
    FEED_UPDATED,
    /** Yönetici beslemeyi etkinleştirdi; otomatik kapanmış beslemede hata sayacı sıfırlanır. */
    FEED_ENABLED,
    /** Yönetici beslemeyi devre dışı bıraktı. */
    FEED_DISABLED
}
