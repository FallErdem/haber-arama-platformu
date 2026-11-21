"""Kaynak içeriğinin silinmesi (FG-YP-14): gerçek PostgreSQL (işçinin kendi kullanıcısıyla) ve gerçek MinIO."""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

import psycopg
import pytest
from conftest import MEDIA_BUCKET, STORAGE_WORKER_USER
from test_media import add_article

from news_worker.audit import AuditRepository
from news_worker.database import Database
from news_worker.object_storage import ObjectStorage, StorageUnavailableError, create_storage_client
from news_worker.source_purge import SourcePurger, SourcePurgeRepository

if TYPE_CHECKING:
    from types_boto3_s3 import S3Client


def build_purger(database: Database, storage: ObjectStorage, batch_size: int = 500) -> SourcePurger:
    return SourcePurger(
        database, SourcePurgeRepository(), AuditRepository(), storage, interval_seconds=60, batch_size=batch_size
    )


@pytest.fixture
def ntv_feed(admin: psycopg.Connection) -> tuple[UUID, UUID]:
    """Silinmeyecek ikinci bir kaynak (NTV) ve beslemesi: silmenin yalnızca istenen kaynağa dokunduğunu gösterir."""
    row = admin.execute(
        "SELECT s.id, f.id FROM feeds f JOIN sources s ON s.id = f.source_id "
        "WHERE s.code = 'NTV' ORDER BY f.name LIMIT 1"
    ).fetchone()
    assert row is not None
    return row[0], row[1]


def store_images(admin: psycopg.Connection, storage_client: S3Client, source_id: UUID) -> list[str]:
    """Kaynağın bekleyen görsellerini indirilmiş sayar ve dosyalarını MinIO'ya yükler; anahtarları döner."""
    rows = admin.execute(
        """
        UPDATE media m
        SET status = 'DOWNLOADED', storage_key = 'articles/' || m.article_id || '/' || m.id
        FROM articles a
        WHERE a.id = m.article_id AND a.source_id = %s
        RETURNING m.storage_key
        """,
        (source_id,),
    ).fetchall()
    keys = [row[0] for row in rows]
    for key in keys:
        storage_client.put_object(Bucket=MEDIA_BUCKET, Key=key, Body=b"gorsel", ContentType="image/webp")
    return keys


def stored_keys(storage_client: S3Client) -> set[str]:
    listed = storage_client.list_objects_v2(Bucket=MEDIA_BUCKET, Prefix="articles/")
    return {item["Key"] for item in listed.get("Contents", [])}


def request_purge(admin: psycopg.Connection, source_id: UUID) -> None:
    """API'nin yaptığını taklit eder: kaynak devre dışıdır ve silme istenmiştir."""
    admin.execute("UPDATE sources SET enabled = false, purge_requested_at = now() WHERE id = %s", (source_id,))


def article_ids(admin: psycopg.Connection, source_id: UUID) -> set[UUID]:
    return {row[0] for row in admin.execute("SELECT id FROM articles WHERE source_id = %s", (source_id,))}


def purge_requested_at(admin: psycopg.Connection, source_id: UUID) -> datetime | None:
    row = admin.execute("SELECT purge_requested_at FROM sources WHERE id = %s", (source_id,)).fetchone()
    assert row is not None
    value: datetime | None = row[0]
    return value


def purged_events(admin: psycopg.Connection, source_id: UUID, since: datetime) -> list[tuple[Any, ...]]:
    """Testin başından beri yazılan silme kayıtları; audit kayıtları silinemediği için zamanla süzülür."""
    return admin.execute(
        "SELECT actor_type, actor_user_id, target_type, result, details FROM audit_events "
        "WHERE action = 'SOURCE_PURGED' AND target_id = %s AND occurred_at >= %s",
        (source_id, since),
    ).fetchall()


def now(admin: psycopg.Connection) -> datetime:
    row = admin.execute("SELECT now()").fetchone()
    assert row is not None
    value: datetime = row[0]
    return value


async def test_files_articles_and_index_documents_of_the_source_are_deleted(
    database: Database,
    admin: psycopg.Connection,
    trt_feed: tuple[UUID, UUID],
    ntv_feed: tuple[UUID, UUID],
    storage: ObjectStorage,
    storage_client: S3Client,
) -> None:
    """Kaynağın görsel dosyaları, haberleri ve haberlerine bağlı satırlar silinir; her haber için belgesinin
    silinmesi notu yazılır; istek boşaltılır ve audit'e yazılır. Başka kaynağın içeriğine dokunulmaz."""
    started_at = now(admin)
    for number in range(1, 4):
        await add_article(database, trt_feed, number=number, images=2)
    await add_article(database, ntv_feed, number=9, images=1)
    trt_keys = store_images(admin, storage_client, trt_feed[0])
    ntv_keys = store_images(admin, storage_client, ntv_feed[0])
    trt_articles = article_ids(admin, trt_feed[0])
    # Bir kullanıcı TRT haberini kaydetmiş: işçinin kullanıcı tablolarına yetkisi yoktur.
    admin.execute(
        "INSERT INTO users (keycloak_sub, email, role, status) VALUES ('okur', 'okur@example.test', 'USER', 'ACTIVE')"
    )
    admin.execute(
        "INSERT INTO saved_articles (user_id, article_id) SELECT (SELECT id FROM users), %s",
        (next(iter(trt_articles)),),
    )
    request_purge(admin, trt_feed[0])

    await build_purger(database, storage).purge_requested(asyncio.Event())

    assert article_ids(admin, trt_feed[0]) == set()
    assert stored_keys(storage_client) == set(ntv_keys)
    assert len(trt_keys) == 6
    # Görsel ve kaydedilme satırları zincirleme silinir (ON DELETE CASCADE); işçinin saved_articles
    # yetkisi olmasa da: zincirleme silmeyi PostgreSQL tablonun sahibinin yetkisiyle yapar.
    assert admin.execute("SELECT count(*) FROM saved_articles").fetchone() == (0,)
    remaining_media = admin.execute("SELECT count(*) FROM media WHERE article_id = ANY(%s)", (list(trt_articles),))
    assert remaining_media.fetchone() == (0,)
    deleted_notes = admin.execute(
        "SELECT article_id FROM outbox_events WHERE operation = 'DELETE' AND status = 'PENDING'"
    ).fetchall()
    assert {row[0] for row in deleted_notes} == trt_articles
    assert len(article_ids(admin, ntv_feed[0])) == 1
    assert purge_requested_at(admin, trt_feed[0]) is None
    assert purged_events(admin, trt_feed[0], started_at) == [
        ("SYSTEM", None, "SOURCE", "SUCCESS", {"article_count": 3, "media_count": 6})
    ]


async def test_feed_validators_are_cleared_so_the_next_read_is_unconditional(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], storage: ObjectStorage
) -> None:
    """Silme bitince beslemelerin ETag ve Last-Modified değerleri silinir: kaynak yeniden açılınca sunucu
    "değişmedi" (304) diyemez, beslemede duran haberler geri gelir. Başka kaynağın beslemelerine dokunulmaz."""
    await add_article(database, trt_feed, images=0)
    admin.execute("UPDATE feeds SET etag = '\"abc\"', last_modified = 'Sat, 21 Nov 2026 18:02:14 GMT'")
    request_purge(admin, trt_feed[0])

    await build_purger(database, storage).purge_requested(asyncio.Event())

    trt = admin.execute(
        "SELECT count(*) FROM feeds WHERE source_id = %s AND (etag IS NOT NULL OR last_modified IS NOT NULL)",
        (trt_feed[0],),
    ).fetchone()
    others = admin.execute(
        "SELECT count(*) FROM feeds WHERE source_id <> %s AND etag IS NULL", (trt_feed[0],)
    ).fetchone()
    assert trt == (0,)
    assert others == (0,)


async def test_articles_are_deleted_in_batches(
    database: Database,
    admin: psycopg.Connection,
    trt_feed: tuple[UUID, UUID],
    storage: ObjectStorage,
    storage_client: S3Client,
) -> None:
    """Haberler parça parça silinir; parça boyunun katı olmayan sayıda haber de eksiksiz silinir."""
    started_at = now(admin)
    for number in range(1, 6):
        await add_article(database, trt_feed, number=number, images=1)
    store_images(admin, storage_client, trt_feed[0])
    request_purge(admin, trt_feed[0])

    await build_purger(database, storage, batch_size=2).purge_requested(asyncio.Event())

    assert article_ids(admin, trt_feed[0]) == set()
    assert stored_keys(storage_client) == set()
    assert purged_events(admin, trt_feed[0], started_at) == [
        ("SYSTEM", None, "SOURCE", "SUCCESS", {"article_count": 5, "media_count": 5})
    ]


async def test_enabled_source_is_not_purged(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], storage: ObjectStorage
) -> None:
    """Etkin kaynakta silme yapılmaz: silme sürerken yeni haber eklenebilirdi. İstek olduğu gibi kalır."""
    await add_article(database, trt_feed, images=0)
    admin.execute("UPDATE sources SET purge_requested_at = now() WHERE id = %s", (trt_feed[0],))

    await build_purger(database, storage).purge_requested(asyncio.Event())

    assert len(article_ids(admin, trt_feed[0])) == 1
    assert purge_requested_at(admin, trt_feed[0]) is not None


async def test_rows_are_kept_when_files_cannot_be_deleted(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], storage_client: S3Client
) -> None:
    """MinIO'ya ulaşılamazsa satırlara dokunulmaz: dosyanın anahtarı kaybolmaz, silme sonra yeniden denenir."""
    await add_article(database, trt_feed, images=1)
    store_images(admin, storage_client, trt_feed[0])
    request_purge(admin, trt_feed[0])
    unreachable = ObjectStorage(
        create_storage_client("http://127.0.0.1:9", STORAGE_WORKER_USER, "x", timeout_seconds=1), MEDIA_BUCKET
    )

    with pytest.raises(StorageUnavailableError):
        await build_purger(database, unreachable).purge_requested(asyncio.Event())

    assert len(article_ids(admin, trt_feed[0])) == 1
    assert admin.execute("SELECT count(*) FROM outbox_events WHERE operation = 'DELETE'").fetchone() == (0,)
    assert purge_requested_at(admin, trt_feed[0]) is not None


async def test_source_without_articles_is_finished_at_once(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], storage: ObjectStorage
) -> None:
    """Haberi olmayan kaynakta istek hemen boşaltılır ve silme sıfır sayılarla audit'e yazılır."""
    started_at = now(admin)
    request_purge(admin, trt_feed[0])

    await build_purger(database, storage).purge_requested(asyncio.Event())

    assert purge_requested_at(admin, trt_feed[0]) is None
    assert purged_events(admin, trt_feed[0], started_at) == [
        ("SYSTEM", None, "SOURCE", "SUCCESS", {"article_count": 0, "media_count": 0})
    ]


async def test_stop_request_leaves_the_purge_for_the_next_run(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], storage: ObjectStorage
) -> None:
    """İşçi durdurulurken silmeye başlanmaz; istek kalır ve işçi yeniden başlayınca silme yapılır."""
    await add_article(database, trt_feed, images=0)
    request_purge(admin, trt_feed[0])
    stop = asyncio.Event()
    stop.set()

    await build_purger(database, storage).purge_requested(stop)

    assert len(article_ids(admin, trt_feed[0])) == 1
    assert purge_requested_at(admin, trt_feed[0]) is not None
