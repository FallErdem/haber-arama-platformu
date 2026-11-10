-- Haberler, kategorileri ve görselleri (ADR-0011, ADR-0013).

-- Haberler. Tablo bölümlenmez (ADR-0015).
CREATE TABLE articles (
    id              uuid        PRIMARY KEY DEFAULT uuidv7(),
    source_id       uuid        NOT NULL REFERENCES sources (id),
    -- Haberi ilk getiren besleme.
    feed_id         uuid        REFERENCES feeds (id),
    external_id     text        NOT NULL,
    url             text        NOT NULL,
    normalized_url  text        NOT NULL,
    title           text        NOT NULL,
    summary         text,
    -- Temizlenmiş HTML; <img> etiketleri çıkarılmış.
    content         text,
    author          text,
    language        text        NOT NULL CHECK (language IN ('tr', 'en')),
    item_type       text        NOT NULL CHECK (item_type IN ('ARTICLE', 'VIDEO', 'GALLERY')),
    published_at    timestamptz NOT NULL,
    fetched_at      timestamptz NOT NULL,
    lifecycle_state text        NOT NULL CHECK (lifecycle_state IN ('HOT', 'WARM', 'COLD')),
    -- Kaynaklar arası grup kimliği; başka bir tabloya bağlı değildir.
    group_id        uuid,
    hidden          boolean     NOT NULL DEFAULT false,
    hidden_reason   text,
    hidden_at       timestamptz,
    hidden_by       uuid        REFERENCES users (id),
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    -- Tekrar kontrolü: aynı kaynaktan aynı kimlikli veya aynı adresli ikinci haber eklenemez (FG-VT-04).
    UNIQUE (source_id, external_id),
    UNIQUE (source_id, normalized_url),
    -- Gizlenen haberin ne zaman ve kim tarafından gizlendiği bilinmelidir.
    CONSTRAINT articles_hidden_check CHECK (NOT hidden OR (hidden_at IS NOT NULL AND hidden_by IS NOT NULL))
);

CREATE INDEX articles_lifecycle_state_published_at_idx ON articles (lifecycle_state, published_at);
CREATE INDEX articles_source_id_published_at_idx ON articles (source_id, published_at);
CREATE INDEX articles_fetched_at_idx ON articles (fetched_at);

CREATE TRIGGER articles_set_updated_at
    BEFORE UPDATE ON articles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Haber ile kategori arasındaki çoka çok ilişki (ADR-0004).
CREATE TABLE article_categories (
    article_id    uuid        NOT NULL REFERENCES articles (id) ON DELETE CASCADE,
    category_id   uuid        NOT NULL REFERENCES categories (id),
    mapping_level text        NOT NULL CHECK (mapping_level IN ('FEED', 'ITEM')),
    created_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (article_id, category_id)
);

-- Haberlerin görselleri. Tablo aynı zamanda görsel indirme kuyruğudur (ADR-0013).
CREATE TABLE media (
    id              uuid        PRIMARY KEY DEFAULT uuidv7(),
    article_id      uuid        NOT NULL REFERENCES articles (id) ON DELETE CASCADE,
    media_type      text        NOT NULL CHECK (media_type IN ('IMAGE', 'VIDEO')),
    -- 0, haberin ana görselidir.
    position        integer     NOT NULL CHECK (position >= 0),
    source_url      text        NOT NULL,
    status          text        NOT NULL CHECK (status IN ('PENDING', 'DOWNLOADED', 'FAILED')),
    attempts        integer     NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    next_attempt_at timestamptz,
    last_error      text,
    -- MinIO'daki anahtar: articles/{article_id}/{media_id}.
    storage_key     text,
    content_type    text,
    size_bytes      bigint      CHECK (size_bytes >= 0),
    width           integer     CHECK (width > 0),
    height          integer     CHECK (height > 0),
    caption         text,
    credit          text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (article_id, source_url),
    -- İndirildiği söylenen bir görselin MinIO'daki yeri bilinmelidir.
    CONSTRAINT media_downloaded_check CHECK (status <> 'DOWNLOADED' OR storage_key IS NOT NULL)
);

-- Görsel indirme işinin "indirilmeyi bekleyen ve zamanı gelmiş görseller" sorgusu için.
CREATE INDEX media_status_next_attempt_at_idx ON media (status, next_attempt_at);

CREATE TRIGGER media_set_updated_at
    BEFORE UPDATE ON media
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();