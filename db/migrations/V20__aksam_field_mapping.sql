-- Akşam'ın alan eşlemesi ve bozuk görsel adreslerinin düzeltilmesi (İ-41).
-- Akşam beslemesindeki <enclosure> adreslerinde klasör adının eğik çizgisi eksiktir
-- (imgsdisk2026/11/24/...; doğrusu imgsdisk/2026/11/24/...) ve bu adresler 404 döner. Aynı görselin
-- doğru adresi haberin içindeki <image> etiketinde de vardır. Eşleme, CNN Türk'te olduğu gibi (V12),
-- okuyucuya ana görseli bu etiketten okumasını söyler; bu etiketten görsel gelen haberde <enclosure> okunmaz.

UPDATE sources
SET field_mapping = '{"image": "image"}'::jsonb
WHERE code = 'AKSAM';

-- Bu betikten önce kaydedilen Akşam görselleri bozuk adresle 404 almıştır (FAILED) ya da henüz denenmemiştir
-- (PENDING). Adresleri düzeltilir ve görseller yeniden indirilmek üzere sıraya konur. Yalnızca bozuk biçimdeki
-- adresler değişir; boş bir veritabanında (testler, yeni kurulum) hiçbir satır etkilenmez.
UPDATE media m
SET source_url = regexp_replace(m.source_url, '/imgsdisk([0-9]{4})/', '/imgsdisk/\1/'),
    status = 'PENDING',
    attempts = 0,
    next_attempt_at = now(),
    last_error = NULL
FROM articles a
JOIN sources s ON s.id = a.source_id
WHERE a.id = m.article_id
  AND s.code = 'AKSAM'
  AND m.status IN ('PENDING', 'FAILED')
  AND m.source_url ~ '/imgsdisk[0-9]{4}/';

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM sources WHERE code = 'AKSAM' AND field_mapping = '{"image": "image"}'::jsonb) THEN
        RAISE EXCEPTION 'AKSAM kaynağı bulunamadı; alan eşlemesi yazılamadı';
    END IF;
END;
$$;
