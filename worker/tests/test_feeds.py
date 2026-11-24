import psycopg
from conftest import count_enabled_feeds

from news_worker.database import Database
from news_worker.feeds import DueFeed, FeedRepository


async def find_due(
    database: Database, limit: int = 100, skipped_reader_types: frozenset[str] = frozenset()
) -> list[DueFeed]:
    async with await database.connect() as connection:
        return await FeedRepository().find_due(connection, limit, skipped_reader_types)


async def test_all_newly_seeded_feeds_are_due(database: Database, admin: psycopg.Connection) -> None:
    """Yeni eklenen beslemelerin hepsinin okuma zamanı gelmiştir."""
    seeded_feed_count = count_enabled_feeds(admin)
    # Sıfır beslemeyle de "hepsi bulundu" denebilirdi; başlangıç verisi gerçekten var olmalı.
    assert seeded_feed_count > 0

    due_feeds = await find_due(database, limit=seeded_feed_count + 1)

    assert len(due_feeds) == seeded_feed_count


async def test_feed_with_future_fetch_time_is_not_returned(database: Database, admin: psycopg.Connection) -> None:
    """Okuma zamanı gelecekte olan besleme dönmez."""
    admin.execute("UPDATE feeds SET next_fetch_at = now() + interval '1 hour'")
    admin.execute(
        "UPDATE feeds SET next_fetch_at = now() - interval '1 minute' "
        "WHERE id = (SELECT id FROM feeds ORDER BY url LIMIT 1)"
    )
    expected = admin.execute(
        "SELECT f.id, s.code, f.name, f.url FROM feeds f JOIN sources s ON s.id = f.source_id ORDER BY f.url LIMIT 1"
    ).fetchone()
    assert expected is not None

    due_feeds = await find_due(database)

    assert [(feed.id, feed.source_code, feed.name, feed.url) for feed in due_feeds] == [expected]


async def test_longest_waiting_feed_comes_first(database: Database, admin: psycopg.Connection) -> None:
    """En çok bekleyen besleme önce gelir."""
    admin.execute(
        "UPDATE feeds SET next_fetch_at = now() - interval '2 hours' "
        "WHERE id = (SELECT id FROM feeds ORDER BY url DESC LIMIT 1)"
    )
    longest_waiting = admin.execute("SELECT id FROM feeds ORDER BY url DESC LIMIT 1").fetchone()
    assert longest_waiting is not None

    due_feeds = await find_due(database)

    assert due_feeds[0].id == longest_waiting[0]


async def test_at_most_limit_feeds_are_returned(database: Database, admin: psycopg.Connection) -> None:
    """Bir turda en fazla istenen sayıda besleme döner."""
    due_feeds = await find_due(database, limit=5)

    assert len(due_feeds) == 5


async def test_disabled_feed_is_not_returned(database: Database, admin: psycopg.Connection) -> None:
    """Devre dışı besleme dönmez."""
    disabled = admin.execute("SELECT id FROM feeds ORDER BY url LIMIT 1").fetchone()
    assert disabled is not None
    admin.execute("UPDATE feeds SET enabled = false, disabled_reason = 'MANUAL' WHERE id = %s", disabled)
    remaining_feed_count = count_enabled_feeds(admin)

    due_feeds = await find_due(database, limit=remaining_feed_count + 1)

    assert len(due_feeds) == remaining_feed_count
    assert disabled[0] not in [feed.id for feed in due_feeds]


async def test_due_feed_carries_reader_type_and_daily_request_limit(
    database: Database, admin: psycopg.Connection
) -> None:
    """Okuyucunun seçimi ve günlük istek bütçesi için kaynağın okuyucu türü ve günlük sınırı da gelir (V22)."""
    due_feeds = await find_due(database, limit=count_enabled_feeds(admin) + 1)

    nyt = next(feed for feed in due_feeds if feed.source_code == "NYT")
    trt = next(feed for feed in due_feeds if feed.source_code == "TRT")
    assert (nyt.reader_type, nyt.daily_request_limit) == ("NYT_TOP_STORIES", 400)
    assert (trt.reader_type, trt.daily_request_limit) == ("RSS", None)


async def test_feeds_of_skipped_reader_types_are_not_returned(database: Database, admin: psycopg.Connection) -> None:
    """Anahtarı tanımlı olmayan okuyucu türünün (NYT) beslemeleri hiç seçilmez."""
    enabled_feed_count = count_enabled_feeds(admin)

    due_feeds = await find_due(database, enabled_feed_count + 1, frozenset({"NYT_TOP_STORIES"}))

    assert due_feeds
    assert all(feed.reader_type != "NYT_TOP_STORIES" for feed in due_feeds)
    assert len(due_feeds) == enabled_feed_count - 11


async def test_feeds_of_disabled_source_are_not_returned(database: Database, admin: psycopg.Connection) -> None:
    """Devre dışı kaynağın beslemeleri dönmez."""
    admin.execute("UPDATE sources SET enabled = false")

    due_feeds = await find_due(database)

    assert due_feeds == []
