"""Yahoo Finance okuyucusunun testleri. Yahoo `respx` ile taklit edilir; testler internete çıkmaz."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
import pytest
import respx

from news_worker.feed_fetcher import create_http_client
from news_worker.market_quotes import Quote
from news_worker.yahoo_finance import YahooFinanceClient, parse_chart

USD_URL = "https://query1.finance.yahoo.com/v8/finance/chart/USDTRY=X"


def chart_body(price: Any = 50.785, previous_close: Any = 50.7185, currency: str = "TRY") -> dict[str, Any]:
    """Yahoo'nun grafik yanıtının kullandığımız kısmı (27 Kasım 2026'daki gerçek yanıttan kısaltıldı)."""
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "currency": currency,
                        "symbol": "USDTRY=X",
                        "regularMarketPrice": price,
                        "chartPreviousClose": previous_close,
                        "regularMarketTime": 1795785037,
                        "regularMarketChangePercent": 0.1312,
                    }
                }
            ],
            "error": None,
        }
    }


@pytest.fixture
def client() -> YahooFinanceClient:
    return YahooFinanceClient(create_http_client("HaberAramaPlatformu/test", 5))


def test_chart_response_is_read_into_a_quote() -> None:
    """Fiyat, önceki kapanış, para birimi ve zaman okunur; sayılar ikili kesir artığı olmadan Decimal olur."""
    quote = parse_chart(chart_body())

    assert quote == Quote(
        price=Decimal("50.785"),
        previous_close=Decimal("50.7185"),
        currency="TRY",
        market_time=datetime.fromtimestamp(1795785037, tz=UTC),
    )


@pytest.mark.parametrize(
    "body",
    [
        {"chart": {"result": None, "error": {"code": "Not Found"}}},
        {"chart": {"result": []}},
        chart_body(price=None),
        chart_body(price="50,78"),
        chart_body(price=True),
        chart_body(price=0),
        chart_body(previous_close=-1),
    ],
    ids=["unknown-symbol", "empty-result", "missing-price", "price-as-text", "price-as-bool", "zero", "negative"],
)
def test_unexpected_chart_response_is_rejected(body: dict[str, Any]) -> None:
    """Bilinmeyen sembol, eksik alan veya geçersiz fiyat hata verir; tabloya yanlış değer yazılmaz."""
    with pytest.raises((ValueError, KeyError, TypeError, IndexError)):
        parse_chart(body)


async def test_quote_is_fetched_with_the_daily_range(client: YahooFinanceClient, respx_mock: respx.MockRouter) -> None:
    """Sembolün grafik adresi yalnızca günlük değerle istenir ve yanıt değere çevrilir."""
    route = respx_mock.get(USD_URL, params={"range": "1d", "interval": "1d"}).respond(200, json=chart_body())

    quote = await client.fetch("USDTRY=X")

    assert quote is not None
    assert quote.price == Decimal("50.785")
    assert route.called


@pytest.mark.parametrize("status", [404, 429, 500])
async def test_http_error_returns_nothing_and_is_logged(
    client: YahooFinanceClient, respx_mock: respx.MockRouter, caplog: pytest.LogCaptureFixture, status: int
) -> None:
    """Yahoo hata dönerse değer yoktur; neden loga yazılır, hata fırlatılmaz."""
    respx_mock.get(USD_URL).respond(status)

    assert await client.fetch("USDTRY=X") is None
    assert f"Piyasa değeri okunamadı: USDTRY=X (HTTP {status})" in caplog.messages


async def test_network_error_returns_nothing(
    client: YahooFinanceClient, respx_mock: respx.MockRouter, caplog: pytest.LogCaptureFixture
) -> None:
    """Bağlantı kurulamazsa değer yoktur; bir sonraki turda yeniden denenir."""
    respx_mock.get(USD_URL).mock(side_effect=httpx.ConnectError("bağlanılamadı"))

    assert await client.fetch("USDTRY=X") is None
    assert "Piyasa değeri okunamadı: USDTRY=X (ağ hatası: ConnectError)" in caplog.messages


async def test_response_that_is_not_json_returns_nothing(
    client: YahooFinanceClient, respx_mock: respx.MockRouter
) -> None:
    """JSON yerine bir HTML sayfası gelirse (ör. Yahoo'nun onay sayfası) değer yoktur."""
    respx_mock.get(USD_URL).respond(200, text="<html>consent</html>")

    assert await client.fetch("USDTRY=X") is None
