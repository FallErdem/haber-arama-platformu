-- Haber metinleri (özet, tam metin, yazar) yalnızca Elasticsearch'te tutulur (ADR-0019).
--
-- Bu betikten önce görünür haberlerin metinleri Elasticsearch'e aktarılmış olmalıdır (1. adımdaki tam
-- yeniden indeksleme). Henüz aktarılmamış metinler sütunlar silinmeden önce outbox notlarına taşınır;
-- kümede uygulama sırası scripts/dev/apply-v14.sh betiğindedir.

-- Yeni bir haberin metinleri, haberle aynı işlemde yazılan outbox notunda taşınır. Not Elasticsearch'e
-- aktarılınca metin nottan silinir (payload boşaltılır); PostgreSQL'de metnin kopyası kalmaz.
-- Meta veri değişikliklerinin notları (kategori eklenmesi, gizleme) metin taşımaz.
ALTER TABLE outbox_events ADD COLUMN payload jsonb;

-- İşlenmemiş notlar: işçi durdurulduğu an son kaydettiği haberlerin notları henüz aktarılmamış olabilir.
-- Metinleri nota konur; yeni işçi belgeyi nottaki metinle yazar. Anahtarlar işçinin okuduğu biçimdedir
-- (worker/src/news_worker/search_document.py, ArticleTexts).
UPDATE outbox_events AS event
SET payload = jsonb_build_object('summary', article.summary, 'content', article.content, 'author', article.author)
FROM articles AS article
WHERE event.article_id = article.id
  AND event.status = 'PENDING';

-- Gizlenmiş haberler: eski düzende belgeleri indeksten silinmişti; metinleri yalnızca bu sütunlardaydı.
-- Her biri için metinleriyle bir not yazılır; yeni işçi belgeyi gizli olarak (hidden: true) oluşturur.
INSERT INTO outbox_events (article_id, operation, status, next_attempt_at, payload)
SELECT id, 'INDEX', 'PENDING', now(),
       jsonb_build_object('summary', summary, 'content', content, 'author', author)
FROM articles
WHERE hidden;

ALTER TABLE articles
    DROP COLUMN summary,
    DROP COLUMN content,
    DROP COLUMN author;
