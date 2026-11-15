-- CNN Türk'ün alan eşlemesi (FG-VT-03, İ-10).
-- CNN Türk haberin görselini standart bir alanda değil, haberin içindeki <image> etiketinde verir
-- (RSS 2.0'da <image> yalnızca kanal düzeyinde tanımlıdır). Eşleme, okuyucuya ana görseli
-- bu etiketten okumasını söyler. Diğer kaynaklar görseli standart alanlarda verdiğinden
-- eşlemeleri boş kalır.

UPDATE sources
SET field_mapping = '{"image": "image"}'::jsonb
WHERE code = 'CNNTURK';

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM sources WHERE code = 'CNNTURK' AND field_mapping = '{"image": "image"}'::jsonb) THEN
        RAISE EXCEPTION 'CNNTURK kaynağı bulunamadı; alan eşlemesi yazılamadı';
    END IF;
END;
$$;
