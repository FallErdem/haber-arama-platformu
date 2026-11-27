"""`market_quotes` tablosunun sorguları (issue #79). SQL yalnızca buradadır."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import psycopg
from psycopg.rows import TupleRow


@dataclass(frozen=True)
class Quote:
    """Bir piyasa değerinin son durumu: dolar kuru, ons altın, BIST 100 gibi."""

    price: Decimal
    # Bir önceki günün kapanışı; günlük değişim yüzdesi bundan hesaplanır.
    previous_close: Decimal
    # Fiyatın para birimi: TRY veya USD.
    currency: str
    # Piyasadaki son fiyatın zamanı.
    market_time: datetime


# Her kodun tek satırı vardır: kod ilk kez geliyorsa satır eklenir, varsa güncellenir (upsert).
# EXCLUDED, eklenmek istenen ama çakışma yüzünden eklenemeyen satırın değerleridir.
_SAVE_QUERY = """
    INSERT INTO market_quotes (code, price, previous_close, currency, market_time, fetched_at)
    VALUES (%(code)s, %(price)s, %(previous_close)s, %(currency)s, %(market_time)s, now())
    ON CONFLICT (code) DO UPDATE
    SET price = EXCLUDED.price,
        previous_close = EXCLUDED.previous_close,
        currency = EXCLUDED.currency,
        market_time = EXCLUDED.market_time,
        fetched_at = EXCLUDED.fetched_at
"""


class MarketQuoteRepository:
    async def save(self, connection: psycopg.AsyncConnection[TupleRow], quotes: Mapping[str, Quote]) -> None:
        """Değerleri kodlarıyla kaydeder (`{"USD": Quote(...)}`). Hepsi tek işlemde yazılır."""
        async with connection.transaction():
            for code, quote in quotes.items():
                await connection.execute(
                    _SAVE_QUERY,
                    {
                        "code": code,
                        "price": quote.price,
                        "previous_close": quote.previous_close,
                        "currency": quote.currency,
                        "market_time": quote.market_time,
                    },
                )
