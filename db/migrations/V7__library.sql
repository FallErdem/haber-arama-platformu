-- Kullanıcıya özel işlevler: kaydedilen haberler ve kaydedilmiş aramalar.

CREATE TABLE saved_articles (
    user_id    uuid        NOT NULL REFERENCES users (id),
    article_id uuid        NOT NULL REFERENCES articles (id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, article_id)
);

-- Kullanıcının kaydettiği haberlerin, kaydetme tarihine göre listelenmesi için.
CREATE INDEX saved_articles_user_id_created_at_idx ON saved_articles (user_id, created_at);
-- Bir haber silindiğinde ona ait kayıtların bulunması için (ON DELETE CASCADE).
CREATE INDEX saved_articles_article_id_idx ON saved_articles (article_id);

CREATE TABLE saved_searches (
    id         uuid        PRIMARY KEY DEFAULT uuidv7(),
    user_id    uuid        NOT NULL REFERENCES users (id),
    name       text        NOT NULL,
    query      text,
    -- Kaynak, dil, kategori, göreli tarih aralığı ve sıralama.
    filters    jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, name)
);

CREATE TRIGGER saved_searches_set_updated_at
    BEFORE UPDATE ON saved_searches
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();