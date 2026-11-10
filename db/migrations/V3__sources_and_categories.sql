-- Haber kaynakları, beslemeler, ortak kategoriler ve kaynak kategorilerinin eşlemeleri (ADR-0004, ADR-0013).

-- Haber kaynakları. Yeni kaynaklar yönetim panelinden eklenir; kaynağa özgü bütün ayarlar bu tablodadır.
CREATE TABLE sources (
    id                       uuid        PRIMARY KEY DEFAULT uuidv7(),
    code                     text        NOT NULL UNIQUE,
    name                     text        NOT NULL UNIQUE,
    homepage_url             text        NOT NULL,
    reader_type              text        NOT NULL CHECK (reader_type IN ('RSS', 'ATOM', 'NYT_TOP_STORIES')),
    language                 text        NOT NULL CHECK (language IN ('tr', 'en')),
    request_interval_seconds integer     NOT NULL CHECK (request_interval_seconds > 0),
    -- Son 24 saatteki en fazla istek sayısı; boşsa sınır yoktur.
    daily_request_limit      integer     CHECK (daily_request_limit > 0),
    field_mapping            jsonb,
    license                  text,
    attribution_text         text,
    -- İçerik silme istendiğinde dolar; işçi silmeyi tamamlayınca boşaltır (FG-YP-14).
    purge_requested_at       timestamptz,
    enabled                  boolean     NOT NULL DEFAULT true,
    version                  integer     NOT NULL DEFAULT 0,
    created_at               timestamptz NOT NULL DEFAULT now(),
    updated_at               timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER sources_set_updated_at
    BEFORE UPDATE ON sources
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Ortak kategori listesi. Görünen adlar arayüzün dil dosyalarındadır (FOG-31).
CREATE TABLE categories (
    id           uuid        PRIMARY KEY DEFAULT uuidv7(),
    code         text        NOT NULL UNIQUE,
    kind         text        NOT NULL CHECK (kind IN ('TOPIC', 'TEMPORAL')),
    sort_order   integer     NOT NULL,
    -- Doluysa kategori yalnızca bu süre içinde yayımlanan haberleri gösterir (Son Dakika).
    window_hours integer     CHECK (window_hours > 0),
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER categories_set_updated_at
    BEFORE UPDATE ON categories
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Kaynakların beslemeleri. Zamanlama ve sağlık alanlarını işçi günceller (ADR-0013).
CREATE TABLE feeds (
    id                     uuid        PRIMARY KEY DEFAULT uuidv7(),
    source_id              uuid        NOT NULL REFERENCES sources (id),
    name                   text        NOT NULL,
    url                    text        NOT NULL UNIQUE,
    default_category_id    uuid        REFERENCES categories (id),
    use_item_categories    boolean     NOT NULL,
    fetch_interval_minutes integer     NOT NULL DEFAULT 15 CHECK (fetch_interval_minutes > 0),
    next_fetch_at          timestamptz NOT NULL DEFAULT now(),
    etag                   text,
    last_modified          text,
    consecutive_failures   integer     NOT NULL DEFAULT 0 CHECK (consecutive_failures >= 0),
    last_success_at        timestamptz,
    last_error             text,
    enabled                boolean     NOT NULL DEFAULT true,
    disabled_reason        text        CHECK (disabled_reason IN ('MANUAL', 'AUTO')),
    version                integer     NOT NULL DEFAULT 0,
    created_at             timestamptz NOT NULL DEFAULT now(),
    updated_at             timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_id, name),
    -- Devre dışı bir beslemenin nedeni bilinmelidir; etkin bir beslemenin nedeni olamaz.
    CONSTRAINT feeds_enabled_reason_check CHECK (
        (enabled AND disabled_reason IS NULL) OR (NOT enabled AND disabled_reason IS NOT NULL)
    )
);

-- Zamanlayıcının "okuma zamanı gelmiş etkin beslemeler" sorgusu için.
CREATE INDEX feeds_enabled_next_fetch_at_idx ON feeds (enabled, next_fetch_at);

CREATE TRIGGER feeds_set_updated_at
    BEFORE UPDATE ON feeds
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Kaynağın kendi kategori değerinin ortak kategoriye eşlemesi (haber düzeyinde eşleme).
-- source_category normalleştirilmiş olarak saklanır: boşluklar atılmış, kaynağın diline göre küçük harf.
CREATE TABLE category_mappings (
    id              uuid        PRIMARY KEY DEFAULT uuidv7(),
    source_id       uuid        NOT NULL REFERENCES sources (id),
    source_category text        NOT NULL,
    category_id     uuid        NOT NULL REFERENCES categories (id),
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_id, source_category)
);

CREATE TRIGGER category_mappings_set_updated_at
    BEFORE UPDATE ON category_mappings
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();