-- PostgreSQL'deki değişikliklerin Elasticsearch'e aktarılması için outbox (ADR-0012).
-- Kayıt haberin içeriğini taşımaz; işleyen iş haberin güncel halini okur.
CREATE TABLE outbox_events (
    -- uuidv7 zamana göre sıralı olduğundan işleme sırasını da belirler.
    id              uuid        PRIMARY KEY DEFAULT uuidv7(),
    -- Yabancı anahtar değildir: Silinen bir haberin DELETE kaydı, haber silindikten sonra da var olmalıdır.
    article_id      uuid        NOT NULL,
    operation       text        NOT NULL CHECK (operation IN ('INDEX', 'DELETE')),
    status          text        NOT NULL CHECK (status IN ('PENDING', 'PROCESSED')),
    attempts        integer     NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    next_attempt_at timestamptz,
    last_error      text,
    processed_at    timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

-- Aktarım işinin "bekleyen kayıtlar" sorgusu için; yalnızca bekleyen satırları kapsar.
CREATE INDEX outbox_events_pending_next_attempt_at_idx ON outbox_events (next_attempt_at) WHERE status = 'PENDING';

CREATE TRIGGER outbox_events_set_updated_at
    BEFORE UPDATE ON outbox_events
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();