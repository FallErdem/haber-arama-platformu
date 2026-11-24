-- audit-generate.sql'in açtığı deneme bölümlerini (audit_events_deneme_YYYY_MM) kayıtlarıyla birlikte siler.
-- Yalnızca bu adla başlayan bölümler silinir; gerçek kayıtların bölümlerine dokunulmaz.
--
-- Çalıştırma (depo kökünden):
--   kubectl exec -i -n haber postgres-1 -c postgres -- psql -U postgres -d news -v ON_ERROR_STOP=1 \
--     < scripts/dev/volume-data/audit-remove.sql

DO $$
DECLARE
    partition_name text;
    dropped integer := 0;
BEGIN
    FOR partition_name IN
        SELECT c.relname FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid
        WHERE i.inhparent = 'audit_events'::regclass AND c.relname LIKE 'audit\_events\_deneme\_%'
        ORDER BY c.relname
    LOOP
        EXECUTE format('DROP TABLE %I', partition_name);
        dropped := dropped + 1;
    END LOOP;
    RAISE NOTICE '% deneme bölümü silindi', dropped;
END;
$$;

SELECT count(*) AS kalan_audit_kaydi FROM audit_events;
