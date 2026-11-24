-- Ek Türk haber kaynakları (İ-41, ADR-0004 5. bölüm): 16 kaynak, beslemeleri ve kategori eşlemeleri.
-- Besleme adresleri kaynakların kendi sayfalarından alındı ve 24.11.2026'da işçinin kendini tanıttığı adla
-- denendi. Eklenmeyenler: T24 (beslemeye erişilemiyor), Halk TV (besleme güncellenmiyor), Anadolu Ajansı
-- (yalnızca başlık veriyor); Sabah ve Sözcü'nün son dakika beslemeleri (haberlerinde konu bilgisi yok, haberleri
-- konu beslemelerinden de geliyor).

INSERT INTO sources (code, name, homepage_url, reader_type, language, request_interval_seconds, license, attribution_text) VALUES
    ('HURRIYET',    'Hürriyet',        'https://www.hurriyet.com.tr',     'RSS', 'tr', 5, 'Şirket kararı (ADR-0004)', 'Hürriyet'),
    ('MILLIYET',    'Milliyet',        'https://www.milliyet.com.tr',     'RSS', 'tr', 5, 'Şirket kararı (ADR-0004)', 'Milliyet'),
    ('SABAH',       'Sabah',           'https://www.sabah.com.tr',        'RSS', 'tr', 5, 'Şirket kararı (ADR-0004)', 'Sabah'),
    ('SOZCU',       'Sözcü',           'https://www.sozcu.com.tr',        'RSS', 'tr', 5, 'Şirket kararı (ADR-0004)', 'Sözcü'),
    ('CUMHURIYET',  'Cumhuriyet',      'https://www.cumhuriyet.com.tr',   'RSS', 'tr', 5, 'Şirket kararı (ADR-0004)', 'Cumhuriyet'),
    ('BIRGUN',      'BirGün',          'https://www.birgun.net',          'RSS', 'tr', 5, 'Şirket kararı (ADR-0004)', 'BirGün'),
    ('YENISAFAK',   'Yeni Şafak',      'https://www.yenisafak.com',       'RSS', 'tr', 5, 'Şirket kararı (ADR-0004)', 'Yeni Şafak'),
    ('STAR',        'Star',            'https://www.star.com.tr',         'RSS', 'tr', 5, 'Şirket kararı (ADR-0004)', 'Star'),
    ('AKSAM',       'Akşam',           'https://www.aksam.com.tr',        'RSS', 'tr', 5, 'Şirket kararı (ADR-0004)', 'Akşam'),
    ('HABERLERCOM', 'Haberler.com',    'https://www.haberler.com',        'RSS', 'tr', 5, 'Şirket kararı (ADR-0004)', 'Haberler.com'),
    ('KARAR',       'Karar',           'https://www.karar.com',           'RSS', 'tr', 5, 'Şirket kararı (ADR-0004)', 'Karar'),
    ('EURONEWS',    'Euronews Türkçe', 'https://tr.euronews.com',         'RSS', 'tr', 5, 'Şirket kararı (ADR-0004)', 'Euronews Türkçe'),
    ('DW',          'DW Türkçe',       'https://www.dw.com/tr',           'RSS', 'tr', 5, 'Şirket kararı (ADR-0004)', 'DW Türkçe'),
    ('BBCTURKCE',   'BBC Türkçe',      'https://www.bbc.com/turkce',      'RSS', 'tr', 5, 'Şirket kararı (ADR-0004)', 'BBC Türkçe'),
    ('BLOOMBERGHT', 'Bloomberg HT',    'https://www.bloomberght.com',     'RSS', 'tr', 5, 'Şirket kararı (ADR-0004)', 'Bloomberg HT'),
    ('SPUTNIK',     'Sputnik Türkiye', 'https://anlatilaninotesi.com.tr', 'RSS', 'tr', 5, 'Şirket kararı (ADR-0004)', 'Sputnik Türkiye');

-- Kategorisi boş olan beslemeler karışık içeriklidir; kategori her haberin kendi bilgisinden (etiket veya adres) bulunur.
-- Kategori bilgisi vermeyen kaynakların tek beslemesi bir kategoriye eşlenir (Euronews, DW, BBC, Bloomberg HT, Sputnik).
INSERT INTO feeds (source_id, name, url, default_category_id, use_item_categories, fetch_interval_minutes)
SELECT s.id, v.name, v.url, c.id, v.use_item_categories, v.fetch_interval_minutes
FROM (VALUES
    -- Hürriyet
    ('HURRIYET',    'anasayfa',        'https://www.hurriyet.com.tr/rss/anasayfa',                      NULL,           true,  15),
    ('HURRIYET',    'gundem',          'https://www.hurriyet.com.tr/rss/gundem',                        'GENERAL',      false, 15),
    ('HURRIYET',    'dunya',           'https://www.hurriyet.com.tr/rss/dunya',                         'WORLD',        false, 15),
    ('HURRIYET',    'ekonomi',         'https://www.hurriyet.com.tr/rss/ekonomi',                       'ECONOMY',      false, 15),
    ('HURRIYET',    'spor',            'https://www.hurriyet.com.tr/rss/spor',                          'SPORTS',       false, 15),
    ('HURRIYET',    'teknoloji',       'https://www.hurriyet.com.tr/rss/teknoloji',                     'SCIENCE_TECH', false, 15),
    -- Milliyet
    ('MILLIYET',    'sondakika',       'https://www.milliyet.com.tr/rss/rssnew/sondakikarss.xml',       'BREAKING',     true,  5),
    ('MILLIYET',    'dunya',           'https://www.milliyet.com.tr/rss/rssnew/dunyarss.xml',           'WORLD',        false, 15),
    ('MILLIYET',    'teknoloji',       'https://www.milliyet.com.tr/rss/rssnew/teknolojirss.xml',       'SCIENCE_TECH', false, 15),
    -- Sabah
    ('SABAH',       'gundem',          'https://www.sabah.com.tr/rss/gundem.xml',                       'GENERAL',      false, 15),
    ('SABAH',       'dunya',           'https://www.sabah.com.tr/rss/dunya.xml',                        'WORLD',        false, 15),
    ('SABAH',       'ekonomi',         'https://www.sabah.com.tr/rss/ekonomi.xml',                      'ECONOMY',      false, 15),
    ('SABAH',       'spor',            'https://www.sabah.com.tr/rss/spor.xml',                         'SPORTS',       false, 15),
    ('SABAH',       'saglik',          'https://www.sabah.com.tr/rss/saglik.xml',                       'HEALTH',       false, 15),
    ('SABAH',       'teknoloji',       'https://www.sabah.com.tr/rss/teknoloji.xml',                    'SCIENCE_TECH', false, 15),
    ('SABAH',       'kultur-sanat',    'https://www.sabah.com.tr/rss/kultur-sanat.xml',                 'CULTURE_ARTS', false, 15),
    ('SABAH',       'yasam',           'https://www.sabah.com.tr/rss/yasam.xml',                        'LIFESTYLE',    false, 15),
    -- Sözcü
    ('SOZCU',       'gundem',          'https://www.sozcu.com.tr/feeds-rss-category-gundem',            'GENERAL',      false, 15),
    ('SOZCU',       'dunya',           'https://www.sozcu.com.tr/feeds-rss-category-dunya',             'WORLD',        false, 15),
    ('SOZCU',       'ekonomi',         'https://www.sozcu.com.tr/feeds-rss-category-ekonomi',           'ECONOMY',      false, 15),
    ('SOZCU',       'spor',            'https://www.sozcu.com.tr/feeds-rss-category-spor',              'SPORTS',       false, 15),
    ('SOZCU',       'saglik',          'https://www.sozcu.com.tr/feeds-rss-category-saglik',            'HEALTH',       false, 15),
    ('SOZCU',       'bilim-teknoloji', 'https://www.sozcu.com.tr/feeds-rss-category-bilim-teknoloji',   'SCIENCE_TECH', false, 15),
    ('SOZCU',       'kultur-sanat',    'https://www.sozcu.com.tr/feeds-rss-category-kultur-sanat',      'CULTURE_ARTS', false, 15),
    ('SOZCU',       'yasam',           'https://www.sozcu.com.tr/feeds-rss-category-yasam',             'LIFESTYLE',    false, 15),
    -- Cumhuriyet
    ('CUMHURIYET',  'tum-haberler',    'https://www.cumhuriyet.com.tr/rss',                             NULL,           true,  15),
    -- BirGün
    ('BIRGUN',      'tum-haberler',    'https://www.birgun.net/rss/home',                               NULL,           true,  15),
    -- Yeni Şafak
    ('YENISAFAK',   'tum-haberler',    'https://www.yenisafak.com/rss',                                 NULL,           true,  15),
    ('YENISAFAK',   'dunya',           'https://www.yenisafak.com/rss?category=/dunya',                 'WORLD',        false, 15),
    ('YENISAFAK',   'ekonomi',         'https://www.yenisafak.com/rss?category=/ekonomi',               'ECONOMY',      false, 15),
    ('YENISAFAK',   'spor',            'https://www.yenisafak.com/rss?category=/spor',                  'SPORTS',       false, 15),
    ('YENISAFAK',   'teknoloji',       'https://www.yenisafak.com/rss?category=/teknoloji',             'SCIENCE_TECH', false, 15),
    ('YENISAFAK',   'hayat',           'https://www.yenisafak.com/rss?category=/hayat',                 'LIFESTYLE',    false, 15),
    -- Star
    ('STAR',        'mansetler',       'https://www.star.com.tr/rss/mansetler.xml',                     NULL,           true,  15),
    ('STAR',        'guncel',          'https://www.star.com.tr/rss/guncel.xml',                        'GENERAL',      false, 15),
    ('STAR',        'politika',        'https://www.star.com.tr/rss/politika.xml',                      'GENERAL',      false, 15),
    ('STAR',        'dunya',           'https://www.star.com.tr/rss/dunya.xml',                         'WORLD',        false, 15),
    ('STAR',        'ekonomi',         'https://www.star.com.tr/rss/ekonomi.xml',                       'ECONOMY',      false, 15),
    ('STAR',        'spor',            'https://www.star.com.tr/rss/spor.xml',                          'SPORTS',       false, 15),
    ('STAR',        'saglik',          'https://www.star.com.tr/rss/saglik.xml',                        'HEALTH',       false, 15),
    ('STAR',        'teknoloji',       'https://www.star.com.tr/rss/teknoloji.xml',                     'SCIENCE_TECH', false, 15),
    ('STAR',        'sanat',           'https://www.star.com.tr/rss/sanat.xml',                         'CULTURE_ARTS', false, 15),
    -- Akşam
    ('AKSAM',       'tum-haberler',    'https://www.aksam.com.tr/rss/rss.asp',                          NULL,           true,  15),
    -- Haberler.com
    ('HABERLERCOM', 'tum-haberler',    'https://rss.haberler.com/rss.asp',                              NULL,           true,  15),
    -- Karar
    ('KARAR',       'tum-haberler',    'https://www.karar.com/service/rss.php',                         NULL,           true,  15),
    -- Euronews Türkçe
    ('EURONEWS',    'tum-haberler',    'https://tr.euronews.com/rss',                                   'WORLD',        false, 15),
    -- DW Türkçe
    ('DW',          'tum-haberler',    'https://rss.dw.com/xml/rss-tur-all',                            'GENERAL',      false, 15),
    -- BBC Türkçe
    ('BBCTURKCE',   'tum-haberler',    'https://feeds.bbci.co.uk/turkce/rss.xml',                       'GENERAL',      false, 15),
    -- Bloomberg HT
    ('BLOOMBERGHT', 'tum-haberler',    'https://www.bloomberght.com/rss/tum-haberler.xml',              'ECONOMY',      false, 15),
    -- Sputnik Türkiye
    ('SPUTNIK',     'tum-haberler',    'https://anlatilaninotesi.com.tr/export/rss2/archive/index.xml', 'GENERAL',      false, 15)
) AS v (source_code, name, url, category_code, use_item_categories, fetch_interval_minutes)
JOIN sources s ON s.code = v.source_code
LEFT JOIN categories c ON c.code = v.category_code;

-- Haber düzeyindeki eşlemeler: etiket veren kaynaklarda Türkçe küçük harfle etiket, diğerlerinde adresin klasörü.
INSERT INTO category_mappings (source_id, source_category, category_id)
SELECT s.id, v.source_category, c.id
FROM (VALUES
    -- Hürriyet
    ('HURRIYET',    'gündem',                  'GENERAL'),
    ('HURRIYET',    'yerel haberler',          'GENERAL'),
    ('HURRIYET',    'dünya',                   'WORLD'),
    ('HURRIYET',    'avrupa',                  'WORLD'),
    ('HURRIYET',    'ekonomi',                 'ECONOMY'),
    ('HURRIYET',    'spor arena',              'SPORTS'),
    ('HURRIYET',    'teknoloji',               'SCIENCE_TECH'),
    ('HURRIYET',    'eğitim',                  'LIFESTYLE'),
    ('HURRIYET',    'aile',                    'LIFESTYLE'),
    ('HURRIYET',    'lezizz',                  'LIFESTYLE'),
    ('HURRIYET',    'kelebek',                 'LIFESTYLE'),
    ('HURRIYET',    'mahmure',                 'LIFESTYLE'),
    -- Milliyet
    ('MILLIYET',    'gundem',                  'GENERAL'),
    ('MILLIYET',    'siyaset',                 'GENERAL'),
    ('MILLIYET',    'dunya',                   'WORLD'),
    ('MILLIYET',    'ekonomi',                 'ECONOMY'),
    ('MILLIYET',    'spor',                    'SPORTS'),
    ('MILLIYET',    'saglik',                  'HEALTH'),
    ('MILLIYET',    'teknoloji',               'SCIENCE_TECH'),
    ('MILLIYET',    'populer-bilim',           'SCIENCE_TECH'),
    ('MILLIYET',    'oyun-haberleri',          'SCIENCE_TECH'),
    ('MILLIYET',    'kultur-sanat',            'CULTURE_ARTS'),
    ('MILLIYET',    'yasam',                   'LIFESTYLE'),
    ('MILLIYET',    'magazin',                 'LIFESTYLE'),
    -- Cumhuriyet
    ('CUMHURIYET',  'turkiye',                 'GENERAL'),
    ('CUMHURIYET',  'siyaset',                 'GENERAL'),
    ('CUMHURIYET',  'dunya',                   'WORLD'),
    ('CUMHURIYET',  'ekonomi',                 'ECONOMY'),
    ('CUMHURIYET',  'spor',                    'SPORTS'),
    ('CUMHURIYET',  'saglik',                  'HEALTH'),
    ('CUMHURIYET',  'bilim-teknoloji',         'SCIENCE_TECH'),
    ('CUMHURIYET',  'kultur-sanat',            'CULTURE_ARTS'),
    ('CUMHURIYET',  'yasam',                   'LIFESTYLE'),
    ('CUMHURIYET',  'egitim',                  'LIFESTYLE'),
    ('CUMHURIYET',  'gurme',                   'LIFESTYLE'),
    ('CUMHURIYET',  'magazin',                 'LIFESTYLE'),
    -- BirGün
    ('BIRGUN',      'güncel',                  'GENERAL'),
    ('BIRGUN',      'siyaset',                 'GENERAL'),
    ('BIRGUN',      'yurt',                    'GENERAL'),
    ('BIRGUN',      'dünya',                   'WORLD'),
    ('BIRGUN',      'ekonomi',                 'ECONOMY'),
    ('BIRGUN',      'çalışma yaşamı',          'ECONOMY'),
    ('BIRGUN',      'spor',                    'SPORTS'),
    ('BIRGUN',      'teknoloji',               'SCIENCE_TECH'),
    ('BIRGUN',      'bilim',                   'SCIENCE_TECH'),
    ('BIRGUN',      'kültür sanat',            'CULTURE_ARTS'),
    ('BIRGUN',      'eğitim',                  'LIFESTYLE'),
    ('BIRGUN',      'çevre',                   'LIFESTYLE'),
    ('BIRGUN',      'kadın',                   'LIFESTYLE'),
    -- Yeni Şafak
    ('YENISAFAK',   'gündem',                  'GENERAL'),
    ('YENISAFAK',   'yerel gündem',            'GENERAL'),
    ('YENISAFAK',   'türkiye',                 'GENERAL'),
    ('YENISAFAK',   'politika ve siyaset',     'GENERAL'),
    ('YENISAFAK',   'güvenlik ve asayiş',      'GENERAL'),
    ('YENISAFAK',   'dünya',                   'WORLD'),
    ('YENISAFAK',   'küresel gündem',          'WORLD'),
    ('YENISAFAK',   'ortadoğu',                'WORLD'),
    ('YENISAFAK',   'asya',                    'WORLD'),
    ('YENISAFAK',   'avrupa',                  'WORLD'),
    ('YENISAFAK',   'ekonomi',                 'ECONOMY'),
    ('YENISAFAK',   'türkiye ekonomisi',       'ECONOMY'),
    ('YENISAFAK',   'spor',                    'SPORTS'),
    ('YENISAFAK',   'futbol',                  'SPORTS'),
    ('YENISAFAK',   'sağlık',                  'HEALTH'),
    ('YENISAFAK',   'teknoloji',               'SCIENCE_TECH'),
    ('YENISAFAK',   'yapay zeka',              'SCIENCE_TECH'),
    ('YENISAFAK',   'kültür sanat',            'CULTURE_ARTS'),
    ('YENISAFAK',   'hayat',                   'LIFESTYLE'),
    ('YENISAFAK',   'seyahat',                 'LIFESTYLE'),
    ('YENISAFAK',   'eğitim',                  'LIFESTYLE'),
    ('YENISAFAK',   'otomotiv',                'LIFESTYLE'),
    -- Star
    ('STAR',        'guncel',                  'GENERAL'),
    ('STAR',        'politika',                'GENERAL'),
    ('STAR',        'dunya',                   'WORLD'),
    ('STAR',        'ekonomi',                 'ECONOMY'),
    ('STAR',        'spor',                    'SPORTS'),
    ('STAR',        'saglik',                  'HEALTH'),
    ('STAR',        'teknoloji',               'SCIENCE_TECH'),
    ('STAR',        'sanat',                   'CULTURE_ARTS'),
    ('STAR',        'yasam',                   'LIFESTYLE'),
    -- Akşam
    ('AKSAM',       'guncel',                  'GENERAL'),
    ('AKSAM',       'dunya',                   'WORLD'),
    ('AKSAM',       'ekonomi',                 'ECONOMY'),
    ('AKSAM',       'spor',                    'SPORTS'),
    ('AKSAM',       'saglik',                  'HEALTH'),
    ('AKSAM',       'teknoloji',               'SCIENCE_TECH'),
    ('AKSAM',       'kultur-sanat',            'CULTURE_ARTS'),
    ('AKSAM',       'sinema',                  'CULTURE_ARTS'),
    ('AKSAM',       'yasam',                   'LIFESTYLE'),
    ('AKSAM',       'mor-papatya',             'LIFESTYLE'),
    -- Haberler.com
    ('HABERLERCOM', 'guncel',                  'GENERAL'),
    ('HABERLERCOM', 'yerel',                   'GENERAL'),
    ('HABERLERCOM', 'politika',                'GENERAL'),
    ('HABERLERCOM', '3-sayfa',                 'GENERAL'),
    ('HABERLERCOM', 'dunya',                   'WORLD'),
    ('HABERLERCOM', 'ekonomi',                 'ECONOMY'),
    ('HABERLERCOM', 'kripto-para',             'ECONOMY'),
    ('HABERLERCOM', 'spor',                    'SPORTS'),
    ('HABERLERCOM', 'saglik',                  'HEALTH'),
    ('HABERLERCOM', 'teknoloji',               'SCIENCE_TECH'),
    ('HABERLERCOM', 'kultur-sanat',            'CULTURE_ARTS'),
    ('HABERLERCOM', 'egitim',                  'LIFESTYLE'),
    ('HABERLERCOM', 'cevre',                   'LIFESTYLE'),
    ('HABERLERCOM', 'magazin',                 'LIFESTYLE'),
    -- Karar
    ('KARAR',       'guncel-haberler',         'GENERAL'),
    ('KARAR',       'sehir-haberleri',         'GENERAL'),
    ('KARAR',       'dunya-haberleri',         'WORLD'),
    ('KARAR',       'ekonomi-haberleri',       'ECONOMY'),
    ('KARAR',       'spor-haberleri',          'SPORTS'),
    ('KARAR',       'saglik-haberleri',        'HEALTH'),
    ('KARAR',       'kultur-sanat-haberleri',  'CULTURE_ARTS'),
    ('KARAR',       'hayat-haberleri',         'LIFESTYLE')
) AS v (source_code, source_category, category_code)
JOIN sources s ON s.code = v.source_code
JOIN categories c ON c.code = v.category_code;

-- Yanlış yazılmış bir kaynak veya kategori kodu satırın sessizce atlanmasına (veya kategorinin boş kalmasına) yol açar;
-- sayım bunu yakalar. Yalnızca bu betiğin kaynakları sayılır: yönetim panelinden eklenen kaynaklar sonucu etkilemez.
DO $$
DECLARE
    source_count   integer;
    feed_count     integer;
    category_count integer;
    mapping_count  integer;
BEGIN
    SELECT count(*) INTO source_count FROM sources WHERE code IN ('HURRIYET', 'MILLIYET', 'SABAH', 'SOZCU', 'CUMHURIYET', 'BIRGUN', 'YENISAFAK', 'STAR', 'AKSAM', 'HABERLERCOM', 'KARAR', 'EURONEWS', 'DW', 'BBCTURKCE', 'BLOOMBERGHT', 'SPUTNIK');
    SELECT count(*), count(f.default_category_id) INTO feed_count, category_count
    FROM feeds f JOIN sources s ON s.id = f.source_id WHERE s.code IN ('HURRIYET', 'MILLIYET', 'SABAH', 'SOZCU', 'CUMHURIYET', 'BIRGUN', 'YENISAFAK', 'STAR', 'AKSAM', 'HABERLERCOM', 'KARAR', 'EURONEWS', 'DW', 'BBCTURKCE', 'BLOOMBERGHT', 'SPUTNIK');
    SELECT count(*) INTO mapping_count
    FROM category_mappings m JOIN sources s ON s.id = m.source_id WHERE s.code IN ('HURRIYET', 'MILLIYET', 'SABAH', 'SOZCU', 'CUMHURIYET', 'BIRGUN', 'YENISAFAK', 'STAR', 'AKSAM', 'HABERLERCOM', 'KARAR', 'EURONEWS', 'DW', 'BBCTURKCE', 'BLOOMBERGHT', 'SPUTNIK');
    IF source_count <> 16 OR feed_count <> 50 OR category_count <> 42 OR mapping_count <> 112 THEN
        RAISE EXCEPTION 'Beklenmeyen sayılar: % kaynak, % besleme, % kategorili besleme, % eşleme (beklenen 16, 50, 42, 112)',
            source_count, feed_count, category_count, mapping_count;
    END IF;
END;
$$;
