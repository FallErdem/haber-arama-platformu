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
    ACCESS_DENIED
}
