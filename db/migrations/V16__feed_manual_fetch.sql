-- Elle başlatılan toplama (FG-YP-08). İki uygulama doğrudan konuşmadığı için istek tabloda taşınır
-- (ADR-0013): API isteği bu sütuna ve next_fetch_at'e yazar; işçi okumayı ingestion_runs'a MANUAL olarak
-- kaydeder ve okuma bitince sütunu boşaltır. Okuma sürerken yeni bir istek gelirse değer değişmiş olur;
-- işçi o zaman sütunu boşaltmaz ve beslemeyi hemen yeniden okur.
--
-- Yetki: news_app ve news_worker'ın feeds tablosundaki yetkileri tablo düzeyindedir (V9); yeni sütun
-- için ayrıca yetki gerekmez.
ALTER TABLE feeds ADD COLUMN manual_fetch_requested_at timestamptz;
