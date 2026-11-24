-- Hacim testi için deneme audit kayıtları (FOG-07, İ-35): varsayılan 10 milyon.
--
-- Audit tablosu silmeye izin vermez (V8); deneme kayıtları gerçek kayıtlarla karıştırılmaz:
-- - Kayıtlar, gerçek kayıtların başladığı Kasım 2026'dan önceki 24 aya (Kasım 2024 – Ekim 2026) yayılır.
--   Bu aylar için yalnızca deneme kayıtlarının durduğu 24 geçici bölüm (audit_events_deneme_YYYY_MM) açılır.
-- - Her kaydın details alanında "deneme": true bulunur.
-- Temizlik: audit-remove.sql bu bölümleri siler; gerçek kayıtlara dokunulmaz.
--
-- Çalıştırma (depo kökünden; bölüm açmak tablo sahibi veya süper kullanıcı yetkisi ister):
--   kubectl exec -i -n haber postgres-1 -c postgres -- psql -U postgres -d news -v ON_ERROR_STOP=1 \
--     < scripts/dev/volume-data/audit-generate.sql
-- Daha az kayıtla denemek için: psql'e -v total=24000 eklenir.

\if :{?total}
\else
\set total 10000000
\endif
SET volume.total = :total;
SET timezone = 'UTC';

DO $$
DECLARE
    total constant bigint := current_setting('volume.total')::bigint;
    month_start date;
    month_index integer := 0;
    per_month bigint;
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid
        WHERE i.inhparent = 'audit_events'::regclass AND c.relname LIKE 'audit\_events\_deneme\_%'
    ) THEN
        RAISE EXCEPTION 'Deneme bölümleri zaten var; önce audit-remove.sql çalıştırılmalı';
    END IF;

    FOR month_start IN
        SELECT generate_series(DATE '2024-11-01', DATE '2026-10-01', INTERVAL '1 month')::date
    LOOP
        EXECUTE format(
            'CREATE TABLE %I PARTITION OF audit_events FOR VALUES FROM (%L) TO (%L)',
            'audit_events_deneme_' || to_char(month_start, 'YYYY_MM'),
            month_start::text || ' 00:00:00+00',
            (month_start + INTERVAL '1 month')::date::text || ' 00:00:00+00'
        );

        -- Kayıtlar aylara eşit dağılır; bölmeden kalanlar son aya eklenir.
        per_month := total / 24 + CASE WHEN month_index = 23 THEN total % 24 ELSE 0 END;

        -- İşlem türleri, bir yönetim panelinde beklenen sıklıklarla: en çok oturum açma.
        -- 200 kullanıcı ve kimlikler md5'ten türetilir; aynı betik aynı kimlikleri üretir.
        INSERT INTO audit_events (
            occurred_at, actor_type, actor_user_id, action, target_type, target_id, result, request_id, ip_address, details
        )
        SELECT
            month_start + (g::double precision / per_month) * (month_start + INTERVAL '1 month' - month_start),
            CASE WHEN kind >= 0.95 THEN 'SYSTEM' ELSE 'USER' END,
            CASE WHEN kind >= 0.95 THEN NULL ELSE md5('deneme-kullanici-' || (g % 200))::uuid END,
            CASE
                WHEN kind < 0.60 THEN 'SESSION_STARTED'
                WHEN kind < 0.70 THEN 'ACCESS_DENIED'
                WHEN kind < 0.78 THEN 'FETCH_REQUESTED'
                WHEN kind < 0.83 THEN 'FEED_UPDATED'
                WHEN kind < 0.88 THEN 'ARTICLE_HIDDEN'
                WHEN kind < 0.92 THEN 'USER_STATUS_CHANGED'
                WHEN kind < 0.95 THEN 'AUDIT_EXPORTED'
                WHEN kind < 0.98 THEN 'FEED_AUTO_DISABLED'
                ELSE 'SOURCE_PURGED'
            END,
            CASE
                WHEN kind < 0.60 THEN 'USER'
                WHEN kind < 0.70 THEN NULL
                WHEN kind < 0.78 THEN 'SOURCE'
                WHEN kind < 0.83 THEN 'FEED'
                WHEN kind < 0.88 THEN 'ARTICLE'
                WHEN kind < 0.92 THEN 'USER'
                WHEN kind < 0.95 THEN NULL
                WHEN kind < 0.98 THEN 'FEED'
                ELSE 'SOURCE'
            END,
            CASE WHEN kind < 0.60 THEN md5('deneme-kullanici-' || (g % 200))::uuid
                 WHEN kind < 0.70 OR (kind >= 0.92 AND kind < 0.95) THEN NULL
                 ELSE md5('deneme-hedef-' || (g % 5000))::uuid END,
            CASE WHEN kind >= 0.60 AND kind < 0.70 THEN 'FAILURE' ELSE 'SUCCESS' END,
            md5('deneme-istek-' || month_index || '-' || g),
            ('10.42.' || (g % 250) || '.' || (g % 200 + 1))::inet,
            '{"deneme": true}'::jsonb
        FROM generate_series(0, per_month - 1) AS g,
             LATERAL (SELECT ((g * 7919) % 10000) / 10000.0 AS kind) AS k;

        RAISE NOTICE '% : % kayıt', to_char(month_start, 'YYYY-MM'), per_month;
        month_index := month_index + 1;
    END LOOP;
END;
$$;

-- Sorgu planlayıcısı yeni kayıtların dağılımını öğrensin.
ANALYZE audit_events;

SELECT count(*) AS deneme_kaydi FROM audit_events WHERE occurred_at < '2026-11-01+00';
