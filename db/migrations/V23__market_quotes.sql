-- Piyasa verileri (issue #79): dolar, euro, gram altın, ons altın, BIST 100 ve Brent petrol.
--
-- İşçi değerleri Yahoo Finance'ten 15 dakikada bir çeker ve buraya yazar; API ana sayfadaki kutu için okur.
-- Her değerin tek satırı vardır, işçi her turda o satırı günceller; geçmiş tutulmaz.
-- Değişim yüzdesi saklanmaz, fiyat ve önceki kapanıştan hesaplanır. Ekranda görünen adlar dil dosyalarındadır.

CREATE TABLE market_quotes (
    -- USD, EUR, GRAM_GOLD, GOLD_OUNCE, BIST100, BRENT
    code           text        PRIMARY KEY,
    -- Sıfırdan büyük: değişim yüzdesi önceki kapanışa bölünerek hesaplanır.
    price          numeric     NOT NULL CHECK (price > 0),
    previous_close numeric     NOT NULL CHECK (previous_close > 0),
    -- Fiyatın para birimi: TRY veya USD (ons altın ve Brent dolar cinsindendir).
    currency       text        NOT NULL,
    -- Piyasadaki son fiyatın zamanı (Yahoo'nun verdiği).
    market_time    timestamptz NOT NULL,
    -- İşçinin değeri çektiği zaman.
    fetched_at     timestamptz NOT NULL
);

-- API yalnızca okur; işçi ekler ve günceller.
GRANT SELECT ON market_quotes TO news_app;
GRANT SELECT, INSERT, UPDATE ON market_quotes TO news_worker;
