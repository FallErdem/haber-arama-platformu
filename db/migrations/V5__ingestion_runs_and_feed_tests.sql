-- Toplama kayıtları ve besleme testleri (ADR-0013).

-- Her besleme okumasının kaydı. Kaynakların son 24 saatlik istek sayısı da buradan hesaplanır.
CREATE TABLE ingestion_runs (
    id              uuid        PRIMARY KEY DEFAULT uuidv7(),
    feed_id         uuid        NOT NULL REFERENCES feeds (id),
    trigger         text        NOT NULL CHECK (trigger IN ('SCHEDULED', 'MANUAL')),
    status          text        NOT NULL CHECK (status IN ('RUNNING', 'SUCCEEDED', 'NOT_MODIFIED', 'FAILED')),
    started_at      timestamptz NOT NULL,
    finished_at     timestamptz,
    http_status     integer,
    -- Yönlendirmeler takip edildikten sonra varılan adres.
    final_url       text,
    items_received  integer     CHECK (items_received >= 0),
    items_new       integer     CHECK (items_new >= 0),
    items_duplicate integer     CHECK (items_duplicate >= 0),
    items_failed    integer     CHECK (items_failed >= 0),
    error_message   text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

-- Bir beslemenin toplama geçmişi ve kaynakların son 24 saatlik istek sayısı için.
CREATE INDEX ingestion_runs_feed_id_started_at_idx ON ingestion_runs (feed_id, started_at);
-- Saklama süresi dolan kayıtların silinmesi için.
CREATE INDEX ingestion_runs_started_at_idx ON ingestion_runs (started_at);

CREATE TRIGGER ingestion_runs_set_updated_at
    BEFORE UPDATE ON ingestion_runs
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Yöneticinin istediği besleme testleri. Sonuçları kalıcı değildir; kısa süre sonra silinir.
CREATE TABLE feed_tests (
    id           uuid        PRIMARY KEY DEFAULT uuidv7(),
    -- Ayarları kullanılacak kaynak.
    source_id    uuid        NOT NULL REFERENCES sources (id),
    url          text        NOT NULL,
    requested_by uuid        NOT NULL REFERENCES users (id),
    status       text        NOT NULL CHECK (status IN ('PENDING', 'SUCCEEDED', 'FAILED')),
    result       jsonb,
    error        text,
    completed_at timestamptz,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);

-- İşçinin "bekleyen testler" sorgusu için; yalnızca bekleyen satırları kapsar.
CREATE INDEX feed_tests_pending_created_at_idx ON feed_tests (created_at) WHERE status = 'PENDING';

CREATE TRIGGER feed_tests_set_updated_at
    BEFORE UPDATE ON feed_tests
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();