"""Piyasa değerlerini güncelleyen işin testleri. Yahoo `respx` ile taklit edilir, tablo gerçek PostgreSQL'dedir."""

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import psycopg
import pytest
import respx
from psycopg.rows import TupleRow

from news_worker.database import Database
from news_worker.feed_fetcher import create_http_client
from news_worker.market_quote_updater import YAHOO_SYMBOLS, MarketQuoteUpdater, gram_gold
from news_worker.market_quotes import MarketQuoteRepository, Quote
from news_worker.yahoo_finance import CHART_URL, YahooFinanceClient

EARLIER = datetime(2026, 11, 27, 9, 0, tzinfo=UTC)
LATER = datetime(2026, 11, 27, 9, 5, tzinfo=UTC)

# Her sembol için sahte değer: (fiyat, önceki kapanış, para birimi).
PRICES: dict[str, tuple[float, float, str]] = {
    "USDTRY=X": (50.0, 49.0, "TRY"),
    "EURTRY=X": (55.0, 55.5, "TRY"),
    "GC=F": (3110.35, 3000.0, "USD"),
    "SI=F": (44.055, 40.538, "USD"),
    "XU100.IS": (11026.26, 10655.7, "TRY"),
    "BZ=F": (91.69, 90.64, "USD"),
    "BTC-USD": (61371.0, 60495.95, "USD"),
}


def chart_body(price: float, previous_close: float, currency: str) -> dict[str, Any]:
    meta = {
        "currency": currency,
        "regularMarketPrice": price,
        "chartPreviousClose": previous_close,
        "regularMarketTime": 1795785037,
    }
    return {"chart": {"result": [{"meta": meta}], "error": None}}


def mock_yahoo(respx_mock: respx.MockRouter, failing: frozenset[str] = frozenset()) -> None:
    """Her sembolün adresine sahte yanıt verir; `failing` içindeki semboller 500 alır."""
    for symbol, (price, previous_close, currency) in PRICES.items():
        route = respx_mock.get(CHART_URL.format(symbol=symbol))
        if symbol in failing:
            route.respond(500)
        else:
            route.respond(200, json=chart_body(price, previous_close, currency))


class FailingRepository(MarketQuoteRepository):
    """Kaydetmeye çalışınca tablo yokmuş gibi hata veren depo (işçi V23'ten önce açıldığında olduğu gibi)."""

    async def save(self, connection: psycopg.AsyncConnection[TupleRow], quotes: Mapping[str, Quote]) -> None:
        raise psycopg.errors.UndefinedTable("market_quotes tablosu yok")


def build_updater(database: Database, repository: MarketQuoteRepository | None = None) -> MarketQuoteUpdater:
    client = YahooFinanceClient(create_http_client("HaberAramaPlatformu/test", 5))
    return MarketQuoteUpdater(database, client, repository or MarketQuoteRepository(), interval_seconds=60)


def saved_codes(admin: psycopg.Connection) -> list[str]:
    return [row[0] for row in admin.execute("SELECT code FROM market_quotes ORDER BY code").fetchall()]


def saved_price(admin: psycopg.Connection, code: str) -> Decimal:
    row = admin.execute("SELECT price FROM market_quotes WHERE code = %s", (code,)).fetchone()
    assert row is not None
    price: Decimal = row[0]
    return price


def test_gram_gold_is_ounce_divided_by_grams_times_dollar() -> None:
    """Gram altın = ons ÷ 31,1035 × dolar; önceki kapanış aynı formülle, zaman ikisinden eskisi."""
    ounce = Quote(Decimal("3110.35"), Decimal("3000"), "USD", LATER)
    usd = Quote(Decimal("50"), Decimal("49"), "TRY", EARLIER)

    gram = gram_gold(ounce, usd)

    # 3110,35 / 31,1035 = 100 (tam bir ons); × 50 = 5000. 3000 / 31,1035 × 49 = 4726,1562 (dört basamağa yuvarlanır).
    assert gram.price == Decimal("5000.0000")
    assert gram.previous_close == Decimal("4726.1562")
    assert gram.currency == "TRY"
    assert gram.market_time == EARLIER


async def test_all_quotes_and_gram_gold_are_saved(
    database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """Yedi sembol okunur, gram altın hesaplanır; sekiz değer tabloya yazılır."""
    mock_yahoo(respx_mock)

    saved = await build_updater(database).update_once()

    assert saved == len(YAHOO_SYMBOLS) + 1
    assert saved_codes(admin) == [
        "BIST100",
        "BITCOIN",
        "BRENT",
        "EUR",
        "GOLD_OUNCE",
        "GRAM_GOLD",
        "SILVER_OUNCE",
        "USD",
    ]
    assert saved_price(admin, "BIST100") == Decimal("11026.26")


async def test_failing_symbol_keeps_its_old_value_and_others_are_saved(
    database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """Bir sembol okunamazsa diğerleri yine yazılır; okunamayanın tablodaki eski değeri kalır."""
    admin.execute(
        "INSERT INTO market_quotes (code, price, previous_close, currency, market_time, fetched_at) "
        "VALUES ('BRENT', 80, 79, 'USD', now(), now())"
    )
    mock_yahoo(respx_mock, failing=frozenset({"BZ=F"}))

    saved = await build_updater(database).update_once()

    assert saved == len(YAHOO_SYMBOLS)
    assert saved_price(admin, "BRENT") == Decimal("80")
    assert saved_price(admin, "USD") == Decimal("50.0")


async def test_gram_gold_is_not_calculated_without_the_dollar_rate(
    database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """Dolar kuru okunamazsa gram altın hesaplanmaz; yanlış bir değer yazılmaz."""
    mock_yahoo(respx_mock, failing=frozenset({"USDTRY=X"}))

    await build_updater(database).update_once()

    assert "GRAM_GOLD" not in saved_codes(admin)
    assert "GOLD_OUNCE" in saved_codes(admin)


async def test_nothing_is_written_when_yahoo_is_unreachable(
    database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """Hiçbir sembol okunamazsa veritabanına bağlanılmaz, tablo değişmez."""
    mock_yahoo(respx_mock, failing=frozenset(PRICES))

    assert await build_updater(database).update_once() == 0
    assert saved_codes(admin) == []


async def test_run_survives_a_failed_round_and_stops_on_request(
    database: Database, respx_mock: respx.MockRouter, caplog: pytest.LogCaptureFixture
) -> None:
    """Kaydetme hata verirse tur loga yazılır, döngü çökmez; durdurma istenince döner."""
    mock_yahoo(respx_mock)
    updater = build_updater(database, FailingRepository())
    stop = asyncio.Event()
    task = asyncio.create_task(updater.run(stop))
    async with asyncio.timeout(5):
        while "Piyasa değerleri kaydedilemedi" not in caplog.messages:  # noqa: ASYNC110
            await asyncio.sleep(0.01)
    stop.set()
    async with asyncio.timeout(5):
        await task
