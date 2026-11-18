-- Kaynağın beslemesindeki saatlerin gerçekte yazıldığı saat dilimi (FG-VT-08).
--
-- CNN Türk saati Türkiye saatiyle yazıp yanına "GMT" koyar (örnek: 15:34 Türkiye saatinde yayımlanan
-- haber "15:34:57 GMT"). Okuyucu bu etikete güvendiği için haberler 3 saat ileri kaydedildi ve
-- "en yeni" sıralamasında hep başa çıktı. Ayar doluysa okuyucu beslemedeki saati bu saat diliminde
-- okur ve yanındaki saat dilimi bilgisini yok sayar; boşsa (diğer kaynaklar) beslemeye güvenilir.
-- Değer IANA saat dilimi adıdır (Europe/Istanbul); tanınmayan bir ad okumayı başarısız yapar ve
-- nedeni toplama geçmişinde görünür.
ALTER TABLE sources ADD COLUMN feed_time_zone text;

UPDATE sources SET feed_time_zone = 'Europe/Istanbul' WHERE code = 'CNNTURK';

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM sources WHERE code = 'CNNTURK' AND feed_time_zone = 'Europe/Istanbul') THEN
        RAISE EXCEPTION 'CNNTURK kaynağı bulunamadı; saat dilimi ayarı yazılamadı';
    END IF;
END;
$$;

-- Eski CNN Türk haberlerinin yayın saati düzeltilir: kaydedilen saat (UTC sanılan) Türkiye saati
-- olarak yeniden okunur. Örnek: 16:28:48 UTC kaydı gerçekte 16:28:48 Türkiye saati, yani 13:28:48 UTC.
--
-- Arama indeksi haberin yayın tarihinin UTC'deki ayına göre aylık indekslere bölünür. Düzeltme bir
-- haberi başka bir aya taşırsa belgesinin başka bir indekse geçmesi gerekir; bu betik bunu yapmaz.
-- Böyle bir haber varsa betik hiçbir şey değiştirmeden durur (betiğin tamamı tek işlemdir).
DO $$
DECLARE
    moving_count integer;
BEGIN
    SELECT count(*) INTO moving_count
    FROM articles a
    JOIN sources s ON s.id = a.source_id
    WHERE s.code = 'CNNTURK'
      AND date_trunc('month', a.published_at AT TIME ZONE 'UTC')
          <> date_trunc('month', ((a.published_at AT TIME ZONE 'UTC') AT TIME ZONE 'Europe/Istanbul') AT TIME ZONE 'UTC');
    IF moving_count > 0 THEN
        RAISE EXCEPTION 'Düzeltme % CNN Türk haberini başka bir aya taşırdı; betik uygulanmadı', moving_count;
    END IF;
END;
$$;

-- Her düzeltilen haber için bir outbox notu: işçi belgenin yayın tarihini günceller. Not metin
-- taşımaz (payload boş); belgede yalnızca meta veri değişir, metinlere dokunulmaz (ADR-0019).
WITH corrected AS (
    UPDATE articles AS article
    SET published_at = (article.published_at AT TIME ZONE 'UTC') AT TIME ZONE 'Europe/Istanbul'
    FROM sources AS source
    WHERE source.id = article.source_id
      AND source.code = 'CNNTURK'
    RETURNING article.id
)
INSERT INTO outbox_events (article_id, operation, status, next_attempt_at)
SELECT id, 'INDEX', 'PENDING', now()
FROM corrected;
