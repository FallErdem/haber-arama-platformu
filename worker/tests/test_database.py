import asyncio
from dataclasses import replace

import psycopg
import pytest

from news_worker.config import Settings
from news_worker.database import Database


async def test_worker_connects_as_news_worker(database: Database) -> None:
    """İşçi veritabanına news_worker kullanıcısıyla bağlanır."""
    async with await database.connect() as connection:
        cursor = await connection.execute("SELECT current_user")
        row = await cursor.fetchone()

    assert row == ("news_worker",)


async def test_schema_is_ready_after_migrations(database: Database) -> None:
    """Geçiş betikleri uygulanmış veritabanında şema hazırdır."""
    assert await database.is_schema_ready() is True


async def test_schema_is_not_ready_without_tables(settings: Settings) -> None:
    """Tabloları olmayan veritabanında şema hazır değildir."""
    empty_database = Database(replace(settings, db_name="empty"))

    assert await empty_database.is_schema_ready() is False


async def test_schema_is_not_ready_when_database_is_unreachable(settings: Settings) -> None:
    """Veritabanına ulaşılamıyorsa şema hazır sayılmaz."""
    # 1 numaralı portta dinleyen bir PostgreSQL yoktur; bağlantı hemen reddedilir.
    unreachable_database = Database(replace(settings, db_port=1))

    assert await unreachable_database.is_schema_ready() is False


async def test_schema_is_not_ready_with_wrong_password(settings: Settings) -> None:
    """Şifre yanlışsa şema hazır sayılmaz."""
    wrong_password_database = Database(replace(settings, db_password="yanlis"))

    assert await wrong_password_database.is_schema_ready() is False


async def test_waiting_ends_immediately_when_schema_is_ready(database: Database) -> None:
    """Tablolar hazırsa bekleme hemen biter."""
    await database.wait_until_ready(asyncio.Event(), timeout_seconds=5)


async def test_waiting_continues_while_schema_is_not_ready(settings: Settings) -> None:
    """Tablolar hazır olmadıkça beklemeye devam eder."""
    empty_database = Database(replace(settings, db_name="empty"))

    with pytest.raises(TimeoutError):
        await empty_database.wait_until_ready(asyncio.Event(), retry_delay_seconds=0.05, timeout_seconds=0.5)


async def test_waiting_ends_when_stop_is_requested(settings: Settings) -> None:
    """Durdurma istenince bekleme biter."""
    empty_database = Database(replace(settings, db_name="empty"))
    stop = asyncio.Event()
    stop.set()

    await empty_database.wait_until_ready(stop, timeout_seconds=5)


async def test_worker_cannot_read_users_table(database: Database) -> None:
    """İşçi kullanıcı tablosunu okuyamaz: en az yetki (ADR-0017)."""
    async with await database.connect() as connection:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            await connection.execute("SELECT count(*) FROM users")
