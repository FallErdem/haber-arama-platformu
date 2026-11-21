package com.erdemgural.newssearch.admin.internal;

import java.util.Arrays;
import java.util.stream.Collectors;

/**
 * Audit kayıtlarının CSV biçimi (API sözleşmesi 6.8; RFC 4180).
 *
 * <p>Her alan çift tırnak içine alınır ve içindeki çift tırnaklar ikilenir: değerdeki virgül, noktalı
 * virgül veya satır sonu yeni bir hücre ya da satır başlatamaz.
 *
 * <p><b>CSV enjeksiyonu:</b> Hesap tablosu programları {@code =}, {@code +}, {@code -} veya {@code @} ile
 * başlayan hücreyi formül olarak çalıştırabilir. Audit kayıtlarında dışarıdan gelen değerler var
 * (kullanıcının seçtiği e-posta, besleme adı, kaynak sitenin hata metni); bu karakterlerle başlayan
 * değerlerin başına {@code '} eklenir. Liste OWASP'ın "CSV Injection" sayfasındakidir: sekme, satır başı,
 * satır sonu ve bazı dillerde formül başlatan tam genişlikli karşılıklar ({@code ＝ ＋ － ＠}) da dahil.
 */
final class AuditCsv {

    /** UTF-8 imza baytları (BOM): Excel, Türkçe karakterleri ancak bununla doğru okur. */
    static final String BOM = "﻿";

    static final String[] HEADER = {
        "id",
        "occurred_at",
        "actor_type",
        "actor_user_id",
        "actor_email",
        "action",
        "target_type",
        "target_id",
        "result",
        "request_id",
        "ip_address",
        "details"
    };

    private static final String FORMULA_STARTS = "=+-@\t\r\n＝＋－＠";

    private AuditCsv() {}

    /** Bir satır; RFC 4180'e göre CRLF ile biter. {@code null} değer boş hücredir. */
    static String line(String... values) {
        return Arrays.stream(values).map(AuditCsv::field).collect(Collectors.joining(",", "", "\r\n"));
    }

    static String field(String value) {
        if (value == null || value.isEmpty()) {
            return "\"\"";
        }
        String safe = FORMULA_STARTS.indexOf(value.charAt(0)) >= 0 ? "'" + value : value;
        return "\"" + safe.replace("\"", "\"\"") + "\"";
    }
}
