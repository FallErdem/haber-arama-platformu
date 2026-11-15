-- Haber düzeyindeki kategori eşlemeleri (ADR-0004, FG-VT-12, İ-11).
-- Değerler 15 Kasım 2026'da 42 beslemenin tamamı okunarak toplandı.
--
-- source_category normalleştirilmiş olarak saklanır: boşluklar atılmış, kaynağın diline göre küçük harf.
-- Değerin geldiği yer kaynağa göre değişir:
--   NTV ve Global Voices: haberin kategori etiketi.
--   TRT ve CNN Türk: kategori etiketi vermezler; haber adresinin klasör kısmı kullanılır
--   (trthaber.com/haber/ekonomi/..., cnnturk.com/dunya/...).
-- Burada bulunmayan bir değer eşlenmez; hiçbir konu kategorisi atanamayan haber Diğer'e düşer (FG-VT-13).

INSERT INTO category_mappings (source_id, source_category, category_id)
SELECT s.id, v.source_category, c.id
FROM (VALUES
    -- TRT Haber (adres)
    ('TRT', 'gundem',          'GENERAL'),
    ('TRT', 'turkiye',         'GENERAL'),
    ('TRT', 'guncel',          'GENERAL'),
    ('TRT', 'savunma',         'GENERAL'),
    ('TRT', 'dunya',           'WORLD'),
    ('TRT', 'turk-dunyasi',    'WORLD'),
    ('TRT', 'ekonomi',         'ECONOMY'),
    ('TRT', 'spor',            'SPORTS'),
    ('TRT', 'saglik',          'HEALTH'),
    ('TRT', 'koronavirus',     'HEALTH'),
    ('TRT', 'bilim-teknoloji', 'SCIENCE_TECH'),
    ('TRT', 'kultur-sanat',    'CULTURE_ARTS'),
    ('TRT', 'yasam',           'LIFESTYLE'),
    ('TRT', 'egitim',          'LIFESTYLE'),
    ('TRT', 'cocuk',           'LIFESTYLE'),
    ('TRT', 'cevre',           'LIFESTYLE'),
    -- NTV (kategori etiketi)
    ('NTV', 'türkiye',   'GENERAL'),
    ('NTV', 'dünya',     'WORLD'),
    ('NTV', 'ekonomi',   'ECONOMY'),
    ('NTV', 'ntvpara',   'ECONOMY'),
    ('NTV', 'spor&skor', 'SPORTS'),
    ('NTV', 'sağlık',    'HEALTH'),
    ('NTV', 'teknoloji', 'SCIENCE_TECH'),
    ('NTV', 'yaşam',     'LIFESTYLE'),
    ('NTV', 'eğitim',    'LIFESTYLE'),
    ('NTV', 'otomobil',  'LIFESTYLE'),
    -- CNN Türk (adres)
    ('CNNTURK', 'turkiye',         'GENERAL'),
    ('CNNTURK', 'yerel-haberler',  'GENERAL'),
    ('CNNTURK', 'dunya',           'WORLD'),
    ('CNNTURK', 'ekonomi',         'ECONOMY'),
    ('CNNTURK', 'spor',            'SPORTS'),
    ('CNNTURK', 'saglik',          'HEALTH'),
    ('CNNTURK', 'bilim-teknoloji', 'SCIENCE_TECH'),
    ('CNNTURK', 'kultur-sanat',    'CULTURE_ARTS'),
    ('CNNTURK', 'yasam',           'LIFESTYLE'),
    ('CNNTURK', 'egitim',          'LIFESTYLE'),
    ('CNNTURK', 'otomobil',        'LIFESTYLE'),
    -- Global Voices (kategori etiketi). Varsayılan kategori Dünya'dır; ülke ve bölge etiketleri eşlenmez.
    ('GLOBALVOICES', 'economics & business', 'ECONOMY'),
    ('GLOBALVOICES', 'health',               'HEALTH'),
    ('GLOBALVOICES', 'technology',           'SCIENCE_TECH'),
    ('GLOBALVOICES', 'science',              'SCIENCE_TECH'),
    ('GLOBALVOICES', 'arts & culture',       'CULTURE_ARTS'),
    ('GLOBALVOICES', 'literature',           'CULTURE_ARTS'),
    ('GLOBALVOICES', 'music',                'CULTURE_ARTS'),
    ('GLOBALVOICES', 'photography',          'CULTURE_ARTS'),
    ('GLOBALVOICES', 'education',            'LIFESTYLE'),
    ('GLOBALVOICES', 'environment',          'LIFESTYLE')
) AS v (source_code, source_category, category_code)
JOIN sources s ON s.code = v.source_code
JOIN categories c ON c.code = v.category_code;

-- Yanlış yazılmış bir kaynak veya kategori kodu, satırın sessizce atlanmasına yol açar; sayım bunu yakalar.
DO $$
DECLARE
    mapping_count integer;
BEGIN
    SELECT count(*) INTO mapping_count FROM category_mappings;
    IF mapping_count <> 47 THEN
        RAISE EXCEPTION 'Beklenmeyen kategori eşlemesi sayısı: % (beklenen 47)', mapping_count;
    END IF;
END;
$$;
