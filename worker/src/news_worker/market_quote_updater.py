"""Piyasa değerlerini düzenli olarak güncelleyen iş (issue #79).

İşçi açılınca bir kez, sonra 15 dakikada bir yedi değeri Yahoo Finance'ten sırayla okur, gram altını hesaplar ve
`market_quotes` tablosuna yazar. API değerleri tablodan okur; dışarıya kendisi istek atmaz.

Okunamayan değerin tablodaki eski satırı olduğu gibi kalır; ekrandaki "son güncelleme" saati bunu gösterir.
"""

import asyncio
import logging
from collections.abc import Mapping
from decimal import Decimal

from news_worker.database import Database, wait_for_stop
from news_worker.market_quotes import MarketQuoteRepository, Quote
from news_worker.yahoo_finance import YahooFinanceClient

log = logging.getLogger(__name__)

# Tablodaki kod → Yahoo sembolü. Ons altın ve ons gümüş (vadeli işlem), Brent ve Bitcoin dolar cinsindendir.
YAHOO_SYMBOLS: Mapping[str, str] = {
    "USD": "USDTRY=X",
    "EUR": "EURTRY=X",
    "GOLD_OUNCE": "GC=F",
    "SILVER_OUNCE": "SI=F",
    "BIST100": "XU100.IS",
    "BRENT": "BZ=F",
    "BITCOIN": "BTC-USD",
}

# Gram altın Yahoo'da yoktur; ons altın ve dolar kurundan hesaplanır.
GRAM_GOLD = "GRAM_GOLD"

# Bir ons (troy ons) altının gram karşılığı.
TROY_OUNCE_GRAMS = Decimal("31.1035")

# Hesaplanan gram altın fiyatı kuruşun altında dört basamağa yuvarlanır.
_FOUR_PLACES = Decimal("0.0001")


def gram_gold(ounce: Quote, usd: Quote) -> Quote:
    """Gram altının TL fiyatı: ons fiyatı (dolar) ÷ 31,1035 × dolar kuru.

    Önceki kapanış da aynı formülle hesaplanır; böylece günlük değişim ons ve kurdaki değişimi birlikte yansıtır.
    Zaman olarak ikisinden eskisi alınır: fiyat en az o kadar güncel değildir. Kapalıçarşı fiyatından biraz farklı
    olabilir; orada alış-satış farkı ve işçilik de vardır.
    """
    return Quote(
        price=(ounce.price / TROY_OUNCE_GRAMS * usd.price).quantize(_FOUR_PLACES),
        previous_close=(ounce.previous_close / TROY_OUNCE_GRAMS * usd.previous_close).quantize(_FOUR_PLACES),
        currency="TRY",
        market_time=min(ounce.market_time, usd.market_time),
    )


class MarketQuoteUpdater:
    def __init__(
        self,
        database: Database,
        client: YahooFinanceClient,
        repository: MarketQuoteRepository,
        interval_seconds: float,
    ) -> None:
        self._database = database
        self._client = client
        self._repository = repository
        self._interval_seconds = interval_seconds

    async def update_once(self) -> int:
        """Bir tur: değerleri okur ve okunabilenleri kaydeder. Kaydedilen değer sayısını döner."""
        quotes: dict[str, Quote] = {}
        # Sırayla: istekler aynı anda gönderilmez, Yahoo'ya yük binmez. Yedi istek birkaç saniye sürer.
        for code, symbol in YAHOO_SYMBOLS.items():
            quote = await self._client.fetch(symbol)
            if quote is not None:
                quotes[code] = quote

        # Gram altın yalnızca ons ve dolar ikisi de okunduysa hesaplanır; biri eksikse eski değer kalır.
        if "GOLD_OUNCE" in quotes and "USD" in quotes:
            quotes[GRAM_GOLD] = gram_gold(quotes["GOLD_OUNCE"], quotes["USD"])

        if quotes:
            async with await self._database.connect() as connection:
                await self._repository.save(connection, quotes)
        return len(quotes)

    async def run(self, stop: asyncio.Event) -> None:
        """İşçi açılınca bir tur yapar, sonra durdurma istenene kadar aralıkla tekrarlar."""
        while not stop.is_set():
            try:
                saved = await self.update_once()
                log.info("Piyasa değerleri güncellendi: %d / %d", saved, len(YAHOO_SYMBOLS) + 1)
            except Exception:
                # Veritabanına yazılamadı (ör. tablo henüz yok); bir sonraki turda yeniden denenir.
                log.exception("Piyasa değerleri kaydedilemedi")
            await wait_for_stop(stop, self._interval_seconds)
