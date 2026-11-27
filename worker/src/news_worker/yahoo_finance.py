"""Yahoo Finance'ten piyasa değerlerinin okunması (issue #79).

Yahoo'nun sitesinin kendi kullandığı grafik adresi okunur (`/v8/finance/chart/<sembol>`). Yanıtın `meta` bölümünde
son fiyat, önceki kapanış, para birimi ve fiyatın zamanı bulunur. Bu, belgelenmiş resmi bir API değildir; Yahoo bir
şeyi değiştirirse okuma başarısız olur ve tablodaki son değer kalır.
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from news_worker.market_quotes import Quote

log = logging.getLogger(__name__)

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

# Yalnızca bugünün günlük değeri istenir; yanıt küçük kalır, önceki kapanış yine `meta`'da gelir.
CHART_PARAMS = {"range": "1d", "interval": "1d"}


class YahooFinanceClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        # Besleme ve görsel indirmeleriyle aynı istemci: aynı User-Agent ve zaman sınırları.
        self._client = client

    async def fetch(self, symbol: str) -> Quote | None:
        """Sembolün son değeri (`USDTRY=X`, `XU100.IS`). Okunamazsa None döner ve nedeni loga yazılır.

        Hata fırlatmaz: bir sembolün okunamaması diğerlerini etkilemesin.
        """
        try:
            response = await self._client.get(CHART_URL.format(symbol=symbol), params=CHART_PARAMS)
        except httpx.HTTPError as error:
            log.warning("Piyasa değeri okunamadı: %s (ağ hatası: %s)", symbol, type(error).__name__)
            return None
        if response.status_code != httpx.codes.OK:
            log.warning("Piyasa değeri okunamadı: %s (HTTP %d)", symbol, response.status_code)
            return None
        try:
            return parse_chart(response.json())
        except (ValueError, KeyError, TypeError, IndexError) as error:
            # JSON değil, alan eksik veya beklenmeyen türde.
            log.warning("Piyasa değerinin yanıtı beklenen biçimde değil: %s (%r)", symbol, error)
            return None


def parse_chart(body: Any) -> Quote:
    """Grafik yanıtından değeri çıkarır. Yanıt beklenen biçimde değilse hata fırlatır."""
    meta = body["chart"]["result"][0]["meta"]
    return Quote(
        price=_positive_decimal(meta["regularMarketPrice"]),
        previous_close=_positive_decimal(meta["chartPreviousClose"]),
        currency=str(meta["currency"]),
        # Yahoo zamanı Unix zamanı (1970'ten beri geçen saniye) olarak verir.
        market_time=datetime.fromtimestamp(int(meta["regularMarketTime"]), tz=UTC),
    )


def _positive_decimal(value: object) -> Decimal:
    """JSON sayısını Decimal'e çevirir. Metin üzerinden çevrilir: 50.785 → Decimal('50.785'), ikili kesir artığı
    (50.78499999...) oluşmaz. Fiyat sıfır veya negatif olamaz."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"Sayı değil: {value!r}")
    result = Decimal(str(value))
    if not result.is_finite() or result <= 0:
        raise ValueError(f"Geçersiz fiyat: {value!r}")
    return result
