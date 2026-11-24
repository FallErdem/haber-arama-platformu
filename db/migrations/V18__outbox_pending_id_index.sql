-- Outbox aktarımı bekleyen notları kimlik sırasıyla, 200'erli alır (news_worker/outbox.py: ORDER BY id LIMIT).
-- Bu indeks olmadan PostgreSQL birincil anahtar indeksinde baştan yürüyor ve her seferinde işlenmiş bütün notların
-- üzerinden geçiyordu; işlenen not arttıkça her tur yavaşladı. 1 milyon deneme haberinin aktarımında hız dakikada
-- 114.600 nottan 11.000'e düştü (İ-35, 24 Kasım 2026).
--
-- Bu kısmi indeks yalnızca bekleyen notları kimlik sırasıyla tutar: sorgu ilk 200 notu doğrudan okur, işlenmiş not
-- sayısı ne olursa olsun süresi aynı kalır. İşlenen not indeksten çıkar; indeks kuyruk kadar küçüktür.
CREATE INDEX outbox_events_pending_id_idx ON outbox_events (id) WHERE status = 'PENDING';
