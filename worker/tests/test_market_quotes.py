"""`market_quotes` tablosunun testleri: gerçek PostgreSQL, işçinin kendi kullanıcısıyla (news_worker)."""

from datetime import UTC, datetime
from decimal import Decimal

import psycopg

from news_worker.database import Database
from news_worker.market_quotes import MarketQuoteRepository, Quote

MORNING = datetime(2026, 11, 27, 7, 0, tzinfo=UTC)
NOON = datetime(2026, 11, 27, 10, 0, tzinfo=UTC)


def quote(price: str, market_time: datetime = MORNING) -> Quote:
    return Quote(price=Decimal(price), previous_close=Decimal("50.0"), currency="TRY", market_time=market_time)


def rows(admin: psycopg.Connection) -> list[tuple[str, Decimal, Decimal, str, datetime]]:
    return admin.execute(
        "SELECT code, price, previous_close, currency, market_time FROM market_quotes ORDER BY code"
    ).fetchall()


async def test_new_quotes_are_inserted(database: Database, admin: psycopg.Connection) -> None:
    """İlk kez gelen kodların satırı eklenir."""
    async with await database.connect() as connection:
        await MarketQuoteRepository().save(connection, {"USD": quote("50.785"), "EUR": quote("55.74")})

    assert rows(admin) == [
        ("EUR", Decimal("55.74"), Decimal("50.0"), "TRY", MORNING),
        ("USD", Decimal("50.785"), Decimal("50.0"), "TRY", MORNING),
    ]


async def test_existing_quote_is_updated_and_others_are_kept(database: Database, admin: psycopg.Connection) -> None:
    """Kayıtlı kodun satırı güncellenir (ikinci satır eklenmez); turda gelmeyen kodun eski satırı kalır."""
    repository = MarketQuoteRepository()
    async with await database.connect() as connection:
        await repository.save(connection, {"USD": quote("50.785"), "EUR": quote("55.74")})
    async with await database.connect() as connection:
        await repository.save(connection, {"USD": quote("51.10", NOON)})

    assert rows(admin) == [
        ("EUR", Decimal("55.74"), Decimal("50.0"), "TRY", MORNING),
        ("USD", Decimal("51.10"), Decimal("50.0"), "TRY", NOON),
    ]
