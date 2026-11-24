-- BirGün'ün "İlgili haberler" kutusundan alınan görsellerin silinmesi (İ-41).
-- Okuyucu bu kutuyu atmaya başlamadan önce (html_cleaner, `inline-related`) kutudaki küçük resimler
-- haberin görseli olarak kaydedildi; bunlar kutuda listelenen başka haberlerin görselleridir. BirGün
-- liste ve kutu küçük resimlerini /resim/list-haber/ yolundan verir; haberin kendi görselleri
-- (/resim/content/) bu yolda değildir.
-- MinIO'daki dosyalar bu betikle silinmez (veritabanı MinIO'ya ulaşamaz); ayrıca silinmeleri gerekir.
-- Boş bir veritabanında (testler, yeni kurulum) hiçbir satır etkilenmez.

DELETE FROM media m
USING articles a, sources s
WHERE a.id = m.article_id
  AND s.id = a.source_id
  AND s.code = 'BIRGUN'
  AND m.source_url LIKE 'https://static.birgun.net/resim/list-haber/%';
