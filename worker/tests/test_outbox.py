"""`OutboxRepository` testleri: gerçek PostgreSQL, işçinin kendi kullanıcısıyla."""

from uuid import UUID

import psycopg

from news_worker.database import Database
from news_worker.outbox import _FIND_DUE_QUERY, OutboxEvent, OutboxRepository

ARTICLE_ID = UUID("019a0000-0000-7000-8000-000000000001")


def add_event(admin: psycopg.Connection, status: str = "PENDING", next_attempt: str = "now()") -> UUID:
    """Bir outbox notu ekler ve kimliğini döner. `next_attempt` bir SQL ifadesidir."""
    row = admin.execute(
        "INSERT INTO outbox_events (article_id, operation, status, next_attempt_at) "
        f"VALUES (%s, 'INDEX', %s, {next_attempt}) RETURNING id",
        (ARTICLE_ID, status),
    ).fetchone()
    assert row is not None
    event_id: UUID = row[0]
    return event_id


async def find_due(database: Database, limit: int = 10) -> list[OutboxEvent]:
    async with await database.connect() as connection:
        return await OutboxRepository().find_due(connection, limit)


async def test_due_events_are_returned_in_creation_order(database: Database, admin: psycopg.Connection) -> None:
    """Bekleyen notlar yazıldıkları sırayla döner; sınır kadarını verir."""
    first = add_event(admin)
    second = add_event(admin)
    add_event(admin)

    events = await find_due(database, limit=2)

    assert events == [OutboxEvent(first, ARTICLE_ID, 0), OutboxEvent(second, ARTICLE_ID, 0)]


async def test_processed_and_postponed_events_are_not_due(database: Database, admin: psycopg.Connection) -> None:
    """İşlenmiş notlar ve deneme zamanı henüz gelmemiş notlar dönmez; zamanı yazılmamış not döner."""
    add_event(admin, status="PROCESSED")
    add_event(admin, next_attempt="now() + interval '5 minutes'")
    without_time = add_event(admin, next_attempt="NULL")

    events = await find_due(database)

    assert [event.id for event in events] == [without_time]


async def test_processed_events_are_marked_with_time(database: Database, admin: psycopg.Connection) -> None:
    """İşlenen not PROCESSED olur ve işlendiği an yazılır; verilmeyen not olduğu gibi kalır."""
    done = add_event(admin)
    waiting = add_event(admin)

    async with await database.connect() as connection:
        await OutboxRepository().mark_processed(connection, [done])

    rows = admin.execute("SELECT id, status, processed_at IS NOT NULL FROM outbox_events ORDER BY id").fetchall()
    assert rows == [(done, "PROCESSED", True), (waiting, "PENDING", False)]


async def test_failed_event_stays_pending_and_is_postponed(database: Database, admin: psycopg.Connection) -> None:
    """Başarısız not PENDING kalır: deneme sayısı artar, hata yazılır, sonraki deneme ileri alınır."""
    event_id = add_event(admin)

    async with await database.connect() as connection:
        await OutboxRepository().record_failure(connection, event_id, "örnek hata", retry_delay_minutes=5)

    row = admin.execute(
        "SELECT status, attempts, last_error, "
        "next_attempt_at BETWEEN now() + interval '4 minutes' AND now() + interval '5 minutes' FROM outbox_events"
    ).fetchone()
    assert row == ("PENDING", 1, "örnek hata", True)
    assert await find_due(database) == []


def test_due_events_are_found_without_reading_processed_ones(admin: psycopg.Connection) -> None:
    """Bekleyen notlar, işlenmiş notların üzerinden geçilmeden bulunur (V18).

    1 milyon deneme haberinin aktarımında sorgu birincil anahtar indeksinde baştan yürüyordu; işlenen not
    arttıkça her tur yavaşladı (dakikada 114.600 nottan 11.000'e; 24 Kasım 2026).
    """
    # Önce işlenmiş, sonra bekleyen notlar: aktarımın ortasındaki durum. Kimlikler oluşturulma sırasıyla artar.
    admin.execute(
        "INSERT INTO outbox_events (article_id, operation, status, next_attempt_at, processed_at) "
        "SELECT gen_random_uuid(), 'INDEX', CASE WHEN g <= 20000 THEN 'PROCESSED' ELSE 'PENDING' END, "
        "       now() - interval '1 minute', CASE WHEN g <= 20000 THEN now() END "
        "FROM generate_series(1, 40000) AS g"
    )
    admin.execute("ANALYZE outbox_events")

    plan = admin.execute("EXPLAIN " + _FIND_DUE_QUERY.replace("%(limit)s", "200")).fetchall()

    assert "outbox_events_pending_id_idx" in "\n".join(line for (line,) in plan)
