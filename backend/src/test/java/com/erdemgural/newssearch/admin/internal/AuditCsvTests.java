package com.erdemgural.newssearch.admin.internal;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

/** Audit CSV'sinin biçimi: RFC 4180 tırnaklama ve CSV enjeksiyonuna karşı önlem (API sözleşmesi 6.8). */
class AuditCsvTests {

    @Test
    @DisplayName("her alan tırnak içine alınır, içteki tırnaklar ikilenir, satır CRLF ile biter")
    void quotesEveryField() {
        assertThat(AuditCsv.line("a", "b,c", "d\"e", "f;g\nh")).isEqualTo("\"a\",\"b,c\",\"d\"\"e\",\"f;g\nh\"\r\n");
    }

    @Test
    @DisplayName("boş değer boş hücredir")
    void nullAndEmptyAreEmptyCells() {
        assertThat(AuditCsv.line(null, "")).isEqualTo("\"\",\"\"\r\n");
    }

    @ParameterizedTest
    @ValueSource(strings = {"=1+2", "+1", "-1", "@SUM(A1)", "\t=1", "\r=1", "\n=1", "＝1", "＋1", "－1", "＠1"})
    @DisplayName("formül başlatan bir karakterle başlayan değerin başına ' eklenir")
    void formulaStartIsPrefixed(String value) {
        assertThat(AuditCsv.field(value)).isEqualTo("\"'" + value + "\"");
    }

    @Test
    @DisplayName("formül karakteri başta değilse değer değişmez")
    void ordinaryValueIsUnchanged() {
        assertThat(AuditCsv.field("2026-11-21T10:00:00Z")).isEqualTo("\"2026-11-21T10:00:00Z\"");
        assertThat(AuditCsv.field("a=b")).isEqualTo("\"a=b\"");
    }

    @Test
    @DisplayName("değerdeki tırnak ve virgül yeni bir hücre başlatamaz")
    void injectionAfterSeparatorStaysInTheSameCell() {
        // Tırnak kapatılıp ",=1+2" ile yeni bir formül hücresi açılmaya çalışılıyor.
        assertThat(AuditCsv.line("x\",=1+2")).isEqualTo("\"x\"\",=1+2\"\r\n");
    }
}
