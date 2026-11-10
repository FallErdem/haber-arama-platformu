-- Başlangıç kaynakları ve beslemeleri (ADR-0003, ADR-0004).
-- Yeni kaynaklar ve beslemeler sonradan yönetim panelinden eklenir.
-- Alan eşlemeleri (field_mapping), okuyucular geliştirilirken eklenecektir (İ-10).
-- NYT, okuyucusuyla birlikte ayrı bir betikle eklenecektir (İ-13).

INSERT INTO sources (code, name, homepage_url, reader_type, language, request_interval_seconds, license, attribution_text) VALUES
    ('TRT',          'TRT Haber',     'https://www.trthaber.com', 'RSS',  'tr', 5,  'Şirket kararı (ADR-0004)', 'TRT Haber'),
    ('NTV',          'NTV',           'https://www.ntv.com.tr',   'ATOM', 'tr', 5,  'Şirket kararı (ADR-0004)', 'NTV'),
    ('CNNTURK',      'CNN Türk',      'https://www.cnnturk.com',  'RSS',  'tr', 5,  'Şirket kararı (ADR-0004)', 'CNN Türk'),
    -- robots.txt: Crawl-delay: 10.
    ('GLOBALVOICES', 'Global Voices', 'https://globalvoices.org', 'RSS',  'en', 10, 'CC BY (Global Voices Attribution Policy)', 'Global Voices');

-- Kategorisi boş olan beslemeler karışık içeriklidir; kategori her haberin kendi bilgisinden bulunur.
-- Son dakika beslemeleri hem Son Dakika kategorisine atanır hem de haber düzeyinde eşlenir.
INSERT INTO feeds (source_id, name, url, default_category_id, use_item_categories, fetch_interval_minutes)
SELECT s.id, v.name, v.url, c.id, v.use_item_categories, v.fetch_interval_minutes
FROM (VALUES
    -- TRT Haber
    ('TRT', 'gundem',          'https://www.trthaber.com/gundem_articles.rss',          'GENERAL',      false, 15),
    ('TRT', 'turkiye',         'https://www.trthaber.com/turkiye_articles.rss',         'GENERAL',      false, 15),
    ('TRT', 'dunya',           'https://www.trthaber.com/dunya_articles.rss',           'WORLD',        false, 15),
    ('TRT', 'ekonomi',         'https://www.trthaber.com/ekonomi_articles.rss',         'ECONOMY',      false, 15),
    ('TRT', 'spor',            'https://www.trthaber.com/spor_articles.rss',            'SPORTS',       false, 15),
    ('TRT', 'saglik',          'https://www.trthaber.com/saglik_articles.rss',          'HEALTH',       false, 15),
    ('TRT', 'bilim_teknoloji', 'https://www.trthaber.com/bilim_teknoloji_articles.rss', 'SCIENCE_TECH', false, 15),
    ('TRT', 'kultur_sanat',    'https://www.trthaber.com/kultur_sanat_articles.rss',    'CULTURE_ARTS', false, 15),
    ('TRT', 'yasam',           'https://www.trthaber.com/yasam_articles.rss',           'LIFESTYLE',    false, 15),
    ('TRT', 'egitim',          'https://www.trthaber.com/egitim_articles.rss',          'LIFESTYLE',    false, 15),
    ('TRT', 'sondakika',       'https://www.trthaber.com/sondakika_articles.rss',       'BREAKING',     true,  5),
    ('TRT', 'manset',          'https://www.trthaber.com/manset_articles.rss',          NULL,           true,  15),
    ('TRT', 'guncel',          'https://www.trthaber.com/guncel_articles.rss',          NULL,           true,  15),
    ('TRT', 'koronavirus',     'https://www.trthaber.com/koronavirus_articles.rss',     NULL,           true,  15),
    ('TRT', 'infografik',      'https://www.trthaber.com/infografik_articles.rss',      NULL,           true,  15),
    ('TRT', 'interaktif',      'https://www.trthaber.com/interaktif_articles.rss',      NULL,           true,  15),
    ('TRT', 'ozel_haber',      'https://www.trthaber.com/ozel_haber_articles.rss',      NULL,           true,  15),
    ('TRT', 'dosya_haber',     'https://www.trthaber.com/dosya_haber_articles.rss',     NULL,           true,  15),
    -- NTV
    ('NTV', 'turkiye',    'https://www.ntv.com.tr/turkiye.rss',    'GENERAL',      false, 15),
    ('NTV', 'dunya',      'https://www.ntv.com.tr/dunya.rss',      'WORLD',        false, 15),
    ('NTV', 'ekonomi',    'https://www.ntv.com.tr/ekonomi.rss',    'ECONOMY',      false, 15),
    ('NTV', 'ntvpara',    'https://www.ntv.com.tr/ntvpara.rss',    'ECONOMY',      false, 15),
    ('NTV', 'sporskor',   'https://www.ntv.com.tr/sporskor.rss',   'SPORTS',       false, 15),
    ('NTV', 'saglik',     'https://www.ntv.com.tr/saglik.rss',     'HEALTH',       false, 15),
    ('NTV', 'teknoloji',  'https://www.ntv.com.tr/teknoloji.rss',  'SCIENCE_TECH', false, 15),
    ('NTV', 'yasam',      'https://www.ntv.com.tr/yasam.rss',      'LIFESTYLE',    false, 15),
    ('NTV', 'egitim',     'https://www.ntv.com.tr/egitim.rss',     'LIFESTYLE',    false, 15),
    ('NTV', 'otomobil',   'https://www.ntv.com.tr/otomobil.rss',   'LIFESTYLE',    false, 15),
    ('NTV', 'son-dakika', 'https://www.ntv.com.tr/son-dakika.rss', 'BREAKING',     true,  5),
    ('NTV', 'galeri',     'https://www.ntv.com.tr/galeri.rss',     NULL,           true,  15),
    ('NTV', 'video',      'https://www.ntv.com.tr/video.rss',      NULL,           true,  15),
    -- CNN Türk
    ('CNNTURK', 'turkiye',      'https://www.cnnturk.com/feed/rss/turkiye/news',      'GENERAL',      false, 15),
    ('CNNTURK', 'dunya',        'https://www.cnnturk.com/feed/rss/dunya/news',        'WORLD',        false, 15),
    ('CNNTURK', 'ekonomi',      'https://www.cnnturk.com/feed/rss/ekonomi/news',      'ECONOMY',      false, 15),
    ('CNNTURK', 'spor',         'https://www.cnnturk.com/feed/rss/spor/news',         'SPORTS',       false, 15),
    ('CNNTURK', 'saglik',       'https://www.cnnturk.com/feed/rss/saglik/news',       'HEALTH',       false, 15),
    ('CNNTURK', 'kultur-sanat', 'https://www.cnnturk.com/feed/rss/kultur-sanat/news', 'CULTURE_ARTS', false, 15),
    ('CNNTURK', 'yasam',        'https://www.cnnturk.com/feed/rss/yasam/news',        'LIFESTYLE',    false, 15),
    ('CNNTURK', 'egitim',       'https://www.cnnturk.com/feed/rss/egitim/news',       'LIFESTYLE',    false, 15),
    ('CNNTURK', 'otomobil',     'https://www.cnnturk.com/feed/rss/otomobil/news',     'LIFESTYLE',    false, 15),
    -- Bilim ve teknoloji haberleri bu besleme üzerinden, haber adresinden eşlenir (ADR-0004).
    ('CNNTURK', 'all',          'https://www.cnnturk.com/feed/rss/all/news',          NULL,           true,  15),
    -- Global Voices: varsayılan Dünya; haberin konu kategorilerinden eşleşenler ayrıca eklenir.
    ('GLOBALVOICES', 'main', 'https://globalvoices.org/feed/', 'WORLD', true, 60)
) AS v (source_code, name, url, category_code, use_item_categories, fetch_interval_minutes)
JOIN sources s ON s.code = v.source_code
LEFT JOIN categories c ON c.code = v.category_code;

-- Yukarıdaki sorgu, yazım hatası olan bir kaynak kodunu sessizce atlar, yazım hatası olan bir
-- kategori kodunu ise sessizce boş bırakır. Bu yüzden sonuç ayrıca kontrol edilir.
DO $$
DECLARE
    feed_count     integer;
    category_count integer;
BEGIN
    SELECT count(*), count(default_category_id) INTO feed_count, category_count FROM feeds;
    IF feed_count <> 42 OR category_count <> 32 THEN
        RAISE EXCEPTION 'Beklenmeyen besleme sayısı: % besleme, % kategorili (beklenen 42 ve 32)',
            feed_count, category_count;
    END IF;
END;
$$;