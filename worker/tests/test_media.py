"""`MediaRepository` testleri: gerçek PostgreSQL, işçinin kendi kullanıcısıyla."""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

import psycopg

from news_worker.articles import ArticleRepository, NewArticle
from news_worker.category_resolver import AssignedCategory, MappingLevel
from news_worker.database import Database
from news_worker.media import MediaRepository, PendingMedia, StoredImage
from news_worker.parsed_article import ItemType, ParsedArticle

PUBLISHED_AT = datetime(2026, 11, 13, 13, 40, tzinfo=UTC)

ARTICLE = ParsedArticle(
    external_id="haber-1",
    url="https://example.test/haber-1",
    normalized_url="https://example.test/haber-1",
    title="Örnek haber",
    summary=None,
    content=None,
    author=None,
    published_at=PUBLISHED_AT,
    item_type=ItemType.ARTICLE,
    image_urls=("https://images.example.test/ana.jpg", "https://images.example.test/ikinci.jpg"),
    source_categories=(),
)


async def add_article(database: Database, feed: tuple[UUID, UUID], number: int = 1, images: int = 2) -> None:
    """Haberi işçinin yaptığı gibi kaydeder; görselleri kendiliğinden PENDING olarak kuyruğa girer."""
    article = replace(
        ARTICLE,
        external_id=f"haber-{number}",
        url=f"https://example.test/haber-{number}",
        normalized_url=f"https://example.test/haber-{number}",
        image_urls=tuple(f"https://images.example.test/{number}-{index}.jpg" for index in range(images)),
    )
    new_article = NewArticle(
        source_id=feed[0],
        feed_id=feed[1],
        language="tr",
        article=article,
        categories=(AssignedCategory("GENERAL", MappingLevel.FEED),),
        fetched_at=PUBLISHED_AT,
    )
    async with await database.connect() as connection:
        assert await ArticleRepository().insert_if_new(connection, new_article)


async def find_due(database: Database, limit: int = 10) -> list[PendingMedia]:
    async with await database.connect() as connection:
        return await MediaRepository().find_due(connection, limit)


def media_rows(admin: psycopg.Connection) -> list[tuple[object, ...]]:
    return admin.execute(
        "SELECT source_url, status, attempts, last_error, storage_key, content_type, size_bytes, width, height "
        "FROM media ORDER BY source_url"
    ).fetchall()


async def test_due_images_carry_their_source_rules(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID]
) -> None:
    """Bekleyen görseller, kaynağın kodu ve istek aralığıyla birlikte, ana görsel önce gelir."""
    await add_article(database, trt_feed)

    due = await find_due(database)

    assert [(item.source_url, item.attempts, item.source_code, item.request_interval_seconds) for item in due] == [
        ("https://images.example.test/1-0.jpg", 0, "TRT", 5),
        ("https://images.example.test/1-1.jpg", 0, "TRT", 5),
    ]


async def test_limit_postponed_and_finished_images(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID]
) -> None:
    """Sınır kadarı döner; deneme zamanı gelmemiş, indirilmiş veya başarısız görsel dönmez."""
    await add_article(database, trt_feed, images=3)
    admin.execute("UPDATE media SET next_attempt_at = now() + interval '5 minutes' WHERE source_url LIKE '%%-1.jpg'")
    admin.execute("UPDATE media SET status = 'FAILED' WHERE source_url LIKE '%%-2.jpg'")

    assert [item.source_url for item in await find_due(database)] == ["https://images.example.test/1-0.jpg"]
    assert await find_due(database, limit=0) == []


async def test_images_of_a_disabled_source_are_not_downloaded(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID]
) -> None:
    """Devre dışı bırakılan kaynağa görsel isteği de atılmaz."""
    await add_article(database, trt_feed)
    admin.execute("UPDATE sources SET enabled = false WHERE code = 'TRT'")

    assert await find_due(database) == []


async def test_downloaded_image_is_recorded_with_its_details(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID]
) -> None:
    """İndirilen görselin depolama anahtarı, türü, boyutu ve ölçüleri yazılır; kuyruktan çıkar."""
    await add_article(database, trt_feed, images=1)
    (media,) = await find_due(database)

    async with await database.connect() as connection:
        await MediaRepository().record_downloaded(
            connection, media.id, StoredImage("articles/a/m", "image/jpeg", 1234, 640, 480)
        )

    assert media_rows(admin) == [
        ("https://images.example.test/1-0.jpg", "DOWNLOADED", 1, None, "articles/a/m", "image/jpeg", 1234, 640, 480)
    ]
    assert await find_due(database) == []


async def test_retry_keeps_image_pending_and_postpones_it(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID]
) -> None:
    """Geçici hatada görsel PENDING kalır; deneme sayısı artar, hata yazılır, deneme ileri alınır."""
    await add_article(database, trt_feed, images=1)
    (media,) = await find_due(database)

    async with await database.connect() as connection:
        await MediaRepository().record_retry(connection, media.id, "HTTP 503", retry_delay_minutes=5)

    row = admin.execute(
        "SELECT status, attempts, last_error, "
        "next_attempt_at BETWEEN now() + interval '4 minutes' AND now() + interval '5 minutes' FROM media"
    ).fetchone()
    assert row == ("PENDING", 1, "HTTP 503", True)
    assert await find_due(database) == []


async def test_failed_image_leaves_the_queue(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID]
) -> None:
    """Başarısız görsel FAILED olur ve bir daha denenmez."""
    await add_article(database, trt_feed, images=1)
    (media,) = await find_due(database)

    async with await database.connect() as connection:
        await MediaRepository().record_failed(connection, media.id, "HTTP 404")

    assert admin.execute("SELECT status, attempts, last_error, next_attempt_at FROM media").fetchall() == [
        ("FAILED", 1, "HTTP 404", None)
    ]
