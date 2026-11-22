"""Bakım işinin testleri: yaşam döngüsü durumu ve eski kayıtların silinmesi. Gerçek PostgreSQL, işçinin kendi
kullanıcısıyla."""

import asyncio
from uuid import UUID, uuid4

import psycopg

from news_worker.database import Database
from news_worker.maintenance import Maintenance, MaintenanceRepository, RetentionPeriods

RETENTION = RetentionPeriods(outbox_days=7, ingestion_run_days=180, feed_test_days=1)


def build_maintenance(
    database: Database, batch_size: int = 1000, retention: RetentionPeriods = RETENTION
) -> Maintenance:
    return Maintenance(database, MaintenanceRepository(), retention, interval_seconds=60, batch_size=batch_size)


def add_article(admin: psycopg.Connection, source_id: UUID, published_ago: str, state: str) -> UUID:
    """Yayın tarihi şu andan `published_ago` kadar önce (`'31 days'`) olan bir haber ekler."""
    key = str(uuid4())
    row = admin.execute(
        """
        INSERT INTO articles (
            source_id, external_id, url, normalized_url, title,
            language, item_type, published_at, fetched_at, lifecycle_state)
        VALUES (%s, %s, %s, %s, 'Haber', 'tr', 'ARTICLE', now() - %s::interval, now(), %s)
        RETURNING id
        """,
        (source_id, key, f"https://example.test/{key}", f"https://example.test/{key}", published_ago, state),
    ).fetchone()
    assert row is not None
    article_id: UUID = row[0]
    return article_id


def state_of(admin: psycopg.Connection, article_id: UUID) -> str:
    row = admin.execute("SELECT lifecycle_state FROM articles WHERE id = %s", (article_id,)).fetchone()
    assert row is not None
    state: str = row[0]
    return state


def count(admin: psycopg.Connection, sql: str) -> int:
    row = admin.execute(sql).fetchone()
    assert row is not None
    value: int = row[0]
    return value


async def test_aging_articles_move_to_warm_and_cold(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID]
) -> None:
    """30 günden eski HOT haber WARM, 1 yıldan eski haber COLD olur; genç haberlere dokunulmaz."""
    source_id = trt_feed[0]
    young = add_article(admin, source_id, "29 days", "HOT")
    month_old = add_article(admin, source_id, "31 days", "HOT")
    year_old_hot = add_article(admin, source_id, "400 days", "HOT")
    year_old_warm = add_article(admin, source_id, "400 days", "WARM")
    already_cold = add_article(admin, source_id, "800 days", "COLD")

    result = await build_maintenance(database).run_once(asyncio.Event())

    assert state_of(admin, young) == "HOT"
    assert state_of(admin, month_old) == "WARM"
    # Bir yıldır güncellenmemiş HOT haber, arada WARM olmadan doğrudan COLD olur.
    assert state_of(admin, year_old_hot) == "COLD"
    assert state_of(admin, year_old_warm) == "COLD"
    assert state_of(admin, already_cold) == "COLD"
    assert (result.became_warm, result.became_cold) == (1, 2)


async def test_work_is_done_in_batches(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID]
) -> None:
    """İş parça parça yapılır; parça boyunun katı olmayan sayıda satır da eksiksiz güncellenir."""
    for _ in range(5):
        add_article(admin, trt_feed[0], "31 days", "HOT")

    result = await build_maintenance(database, batch_size=2).run_once(asyncio.Event())

    assert result.became_warm == 5
    assert count(admin, "SELECT count(*) FROM articles WHERE lifecycle_state = 'HOT'") == 0


async def test_only_processed_outbox_events_past_retention_are_deleted(
    database: Database, admin: psycopg.Connection
) -> None:
    """Süresi dolan işlenmiş not silinir; yeni işlenmiş not ve henüz aktarılmamış (bekleyen) not kalır."""
    admin.execute(
        """
        INSERT INTO outbox_events (article_id, operation, status, processed_at, created_at) VALUES
            (gen_random_uuid(), 'INDEX', 'PROCESSED', now() - interval '8 days', now() - interval '8 days'),
            (gen_random_uuid(), 'INDEX', 'PROCESSED', now() - interval '6 days', now() - interval '6 days'),
            (gen_random_uuid(), 'INDEX', 'PENDING', NULL, now() - interval '30 days')
        """
    )

    result = await build_maintenance(database).run_once(asyncio.Event())

    assert result.deleted_outbox_events == 1
    remaining = admin.execute("SELECT status FROM outbox_events ORDER BY status").fetchall()
    assert remaining == [("PENDING",), ("PROCESSED",)]


async def test_old_ingestion_runs_and_feed_tests_are_deleted(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID]
) -> None:
    """Saklama süresi dolan toplama kayıtları (180 gün) ve besleme testleri (1 gün) silinir; yenileri kalır."""
    source_id, feed_id = trt_feed
    admin.execute(
        """
        INSERT INTO ingestion_runs (feed_id, trigger, status, started_at) VALUES
            (%(feed)s, 'SCHEDULED', 'SUCCEEDED', now() - interval '181 days'),
            (%(feed)s, 'SCHEDULED', 'SUCCEEDED', now() - interval '179 days')
        """,
        {"feed": feed_id},
    )
    admin.execute(
        "INSERT INTO users (keycloak_sub, email, role, status) VALUES ('yonetici', 'y@example.test', 'ADMIN', 'ACTIVE')"
    )
    admin.execute(
        """
        INSERT INTO feed_tests (source_id, url, requested_by, status, created_at)
        SELECT %(source)s, 'https://example.test/feed.xml', id, 'SUCCEEDED', now() - age::interval
        FROM users, unnest(ARRAY['2 days', '1 hour']) AS age
        """,
        {"source": source_id},
    )

    result = await build_maintenance(database).run_once(asyncio.Event())

    assert (result.deleted_ingestion_runs, result.deleted_feed_tests) == (1, 1)
    assert count(admin, "SELECT count(*) FROM ingestion_runs WHERE started_at > now() - interval '180 days'") == 1
    assert count(admin, "SELECT count(*) FROM ingestion_runs") == 1
    assert count(admin, "SELECT count(*) FROM feed_tests") == 1


async def test_retention_periods_come_from_settings(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID]
) -> None:
    """Saklama süreleri ayardan gelir: süre 200 gün olunca 181 günlük toplama kaydı kalır."""
    admin.execute(
        "INSERT INTO ingestion_runs (feed_id, trigger, status, started_at) "
        "VALUES (%s, 'SCHEDULED', 'SUCCEEDED', now() - interval '181 days')",
        (trt_feed[1],),
    )
    longer = RetentionPeriods(outbox_days=7, ingestion_run_days=200, feed_test_days=1)

    result = await build_maintenance(database, retention=longer).run_once(asyncio.Event())

    assert result.deleted_ingestion_runs == 0
    assert count(admin, "SELECT count(*) FROM ingestion_runs") == 1


async def test_stop_request_leaves_the_work_for_the_next_run(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID]
) -> None:
    """İşçi durdurulurken bakıma başlanmaz; iş bir sonraki çalışmada yapılır."""
    article = add_article(admin, trt_feed[0], "31 days", "HOT")
    stop = asyncio.Event()
    stop.set()

    await build_maintenance(database).run_once(stop)

    assert state_of(admin, article) == "HOT"
