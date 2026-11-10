-- Audit log (ADR-0016). Kayıtlar eklendikten sonra değiştirilemez ve silinemez.
-- Tablo aylara bölümlenir; başka tablolara yabancı anahtarla bağlanmaz.
CREATE TABLE audit_events (
    id            uuid        NOT NULL DEFAULT uuidv7(),
    -- Bölümleme anahtarı.
    occurred_at   timestamptz NOT NULL DEFAULT now(),
    actor_type    text        NOT NULL CHECK (actor_type IN ('USER', 'SYSTEM')),
    actor_user_id uuid,
    action        text        NOT NULL,
    target_type   text,
    target_id     uuid,
    result        text        NOT NULL CHECK (result IN ('SUCCESS', 'FAILURE')),
    request_id    text,
    ip_address    inet,
    -- Yalnızca işleme göre önceden tanımlanmış alanlar; parola ve token gibi bilgiler yazılmaz.
    details       jsonb,
    -- Bölümlenmiş tabloda birincil anahtar bölümleme anahtarını içermek zorundadır.
    PRIMARY KEY (id, occurred_at),
    -- Kullanıcının yaptığı işlemde kullanıcı bilinmelidir; sistem işlemlerinde kullanıcı yoktur.
    CONSTRAINT audit_events_actor_check CHECK (
        (actor_type = 'USER' AND actor_user_id IS NOT NULL) OR (actor_type = 'SYSTEM' AND actor_user_id IS NULL)
    )
) PARTITION BY RANGE (occurred_at);

-- Kasım 2026'dan Aralık 2028'e kadar her ay için bir bölüm.
-- Sınırlar açıkça UTC olarak yazılır: Saat dilimi belirtilmezse sınırlar betiği çalıştıran
-- oturumun saat dilimine göre yorumlanır.
DO $$
DECLARE
    month_start date;
BEGIN
    FOR month_start IN
        SELECT generate_series(DATE '2026-11-01', DATE '2028-12-01', INTERVAL '1 month')::date
    LOOP
        EXECUTE format(
            'CREATE TABLE %I PARTITION OF audit_events FOR VALUES FROM (%L) TO (%L)',
            'audit_events_' || to_char(month_start, 'YYYY_MM'),
            month_start::text || ' 00:00:00+00',
            (month_start + INTERVAL '1 month')::date::text || ' 00:00:00+00'
        );
    END LOOP;
END;
$$;

-- Hiçbir aylık bölüme düşmeyen kayıtlar için (örneğin 2029'dan sonraki kayıtlar).
CREATE TABLE audit_events_default PARTITION OF audit_events DEFAULT;

-- Ana tabloda oluşturulan indeksler bütün bölümlere uygulanır.
CREATE INDEX audit_events_occurred_at_idx ON audit_events (occurred_at);
CREATE INDEX audit_events_actor_user_id_occurred_at_idx ON audit_events (actor_user_id, occurred_at);
CREATE INDEX audit_events_action_occurred_at_idx ON audit_events (action, occurred_at);
CREATE INDEX audit_events_target_idx ON audit_events (target_type, target_id);

-- Kayıtların değiştirilmesini ve silinmesini reddeder.
CREATE FUNCTION reject_audit_modification() RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'audit_events kayıtları değiştirilemez ve silinemez (%)', TG_OP;
END;
$$;

-- Satır düzeyindeki tetikleyiciler bütün bölümlere uygulanır.
CREATE TRIGGER audit_events_reject_update_delete
    BEFORE UPDATE OR DELETE ON audit_events
    FOR EACH ROW EXECUTE FUNCTION reject_audit_modification();

-- TRUNCATE, satır tetikleyicilerini çalıştırmadan tabloyu boşalttığı için ayrıca reddedilir.
CREATE TRIGGER audit_events_reject_truncate
    BEFORE TRUNCATE ON audit_events
    FOR EACH STATEMENT EXECUTE FUNCTION reject_audit_modification();