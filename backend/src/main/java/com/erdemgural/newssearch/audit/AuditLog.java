package com.erdemgural.newssearch.audit;

/**
 * Audit log'a kayıt yazma yolu (ADR-0016). Kayıtlar yalnızca eklenir; kalıcı hale gelmiş bir kayıt
 * değiştirilemez ve silinemez (veritabanı yetkileri ve tetikleyici, V8 ve V9).
 */
public interface AuditLog {

    /**
     * Kaydı yazar. Çağıran bir veritabanı işlemi (transaction) içindeyse kayıt o işlemin parçası olur:
     * işlem başarıyla biterse (COMMIT) asıl değişiklik ve audit kaydı birlikte kalıcı olur; işlem bir
     * hatayla yarıda kalırsa (ROLLBACK) ikisi de hiç yazılmamış sayılır. Kayıt sonradan silinmez, "geri
     * alındı" diye ayrı bir kayıt da yazılmaz; kalıcı hale gelmediği için hiçbir zaman var olmamıştır.
     * Böylece yapılmamış bir işlemin kaydı ya da kaydı olmayan bir işlem oluşamaz (ADR-0016 5. bölüm).
     */
    void record(AuditEvent event);
}
