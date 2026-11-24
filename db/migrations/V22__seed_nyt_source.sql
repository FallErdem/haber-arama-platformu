-- New York Times kaynağı, bölüm beslemeleri ve bölüm → kategori eşlemeleri (İ-13, ADR-0009).
--
-- Bölümler Top Stories API'sinden okunur. Günlük istek bütçesi 400'dür (NYT'nin günlük 500 isteğinin %80'i;
-- işçi son 24 saatteki okumaları sayar). world 30 dakikada bir, diğer 10 bölüm saatte bir okunur: günde
-- 48 + 240 = 288 istek; kalan pay hata sonrası yeniden denemelere ve elle okumalara kalır. NYT istekler arasında
-- 12 saniye beklenmesini önerir.
--
-- Ön denemede (24 Kasım 2026) sports bölümü boş döndü (Nisan 2025'ten beri güncellenmiyor), books/review
-- 401 verdi; bu iki bölüm alınmadı. Kitap haberleri arts bölümünün yanıtında books olarak gelir.
--
-- Kategori her haberin kendi bölümünden (section) bulunur: bir bölümün yanıtında başka bölümlerin haberleri de
-- vardır (world yanıtında business, climate, travel). Bu yüzden beslemelerin varsayılan kategorisi yoktur.
-- Eşlenmeyen bölümler (opinion, magazine, podcasts, obituaries, upshot) Diğer'e düşer. ABD'nin iç haberleri
-- (us, politics, nyregion) bu uygulamanın okuru için dış haber olduğundan Dünya'ya eşlenir.
--
-- API anahtarı veritabanında tutulmaz: işçi onu Secret'tan okur ve yalnızca istek anında adrese ekler.

INSERT INTO sources (code, name, homepage_url, reader_type, language, request_interval_seconds, daily_request_limit,
                     license, attribution_text)
VALUES ('NYT', 'The New York Times', 'https://www.nytimes.com', 'NYT_TOP_STORIES', 'en', 12, 400,
        'NYT API kullanım şartları (ADR-0009)', 'Data provided by The New York Times');

INSERT INTO feeds (source_id, name, url, default_category_id, use_item_categories, fetch_interval_minutes)
SELECT s.id, v.name, 'https://api.nytimes.com/svc/topstories/v2/' || v.name || '.json', NULL, true,
       v.fetch_interval_minutes
FROM (VALUES
    ('world',      30),
    ('us',         60),
    ('politics',   60),
    ('business',   60),
    ('technology', 60),
    ('science',    60),
    ('health',     60),
    ('arts',       60),
    ('movies',     60),
    ('travel',     60),
    ('food',       60)
) AS v (name, fetch_interval_minutes)
JOIN sources s ON s.code = 'NYT';

INSERT INTO category_mappings (source_id, source_category, category_id)
SELECT s.id, v.source_category, c.id
FROM (VALUES
    ('us',          'WORLD'),
    ('world',       'WORLD'),
    ('nyregion',    'WORLD'),
    ('politics',    'WORLD'),
    ('weather',     'WORLD'),
    ('business',    'ECONOMY'),
    ('realestate',  'ECONOMY'),
    ('your-money',  'ECONOMY'),
    ('technology',  'SCIENCE_TECH'),
    ('science',     'SCIENCE_TECH'),
    ('climate',     'SCIENCE_TECH'),
    ('health',      'HEALTH'),
    ('well',        'HEALTH'),
    ('sports',      'SPORTS'),
    ('arts',        'CULTURE_ARTS'),
    ('movies',      'CULTURE_ARTS'),
    ('theater',     'CULTURE_ARTS'),
    ('books',       'CULTURE_ARTS'),
    ('travel',      'LIFESTYLE'),
    ('food',        'LIFESTYLE'),
    ('dining',      'LIFESTYLE'),
    ('style',       'LIFESTYLE'),
    ('fashion',     'LIFESTYLE'),
    ('t-magazine',  'LIFESTYLE'),
    ('automobiles', 'LIFESTYLE')
) AS v (source_category, category_code)
JOIN sources s ON s.code = 'NYT'
JOIN categories c ON c.code = v.category_code;

DO $$
DECLARE
    feed_count    integer;
    mapping_count integer;
BEGIN
    SELECT count(*) INTO feed_count FROM feeds f JOIN sources s ON s.id = f.source_id WHERE s.code = 'NYT';
    SELECT count(*) INTO mapping_count FROM category_mappings m JOIN sources s ON s.id = m.source_id WHERE s.code = 'NYT';
    IF feed_count <> 11 OR mapping_count <> 25 THEN
        RAISE EXCEPTION 'Beklenmeyen sayılar: % besleme, % eşleme (beklenen 11, 25)', feed_count, mapping_count;
    END IF;
END;
$$;
