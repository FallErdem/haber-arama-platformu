"""Mevcut görsellerin ortak biçime çevrilmesi: gerçek PostgreSQL ve gerçek MinIO, işçinin yetkileriyle."""

import io
from dataclasses import replace
from typing import TYPE_CHECKING
from uuid import UUID

import psycopg
import pytest
from conftest import MEDIA_BUCKET, make_image
from PIL import Image
from test_media import add_article

from news_worker import convert_media
from news_worker.config import Settings
from news_worker.database import Database
from news_worker.media import MediaRepository
from news_worker.object_storage import ObjectStorage

if TYPE_CHECKING:
    from types_boto3_s3 import S3Client


def store_downloaded(
    admin: psycopg.Connection,
    storage_client: S3Client,
    media_id: UUID,
    body: bytes,
    content_type: str,
    size: tuple[int, int] | None = None,
) -> str:
    """Daha önce indirilmiş (çevrilmemiş) bir görseli kümedeki gibi hazırlar: dosya MinIO'da, satır DOWNLOADED.

    Ölçüler verilmezse dosyadan okunur; bozuk dosya için testin kendisi verir.
    """
    width, height = size or Image.open(io.BytesIO(body)).size
    key = f"articles/test/{media_id}"
    storage_client.put_object(Bucket=MEDIA_BUCKET, Key=key, Body=body, ContentType=content_type)
    admin.execute(
        "UPDATE media SET status = 'DOWNLOADED', storage_key = %s, content_type = %s, size_bytes = %s, "
        "width = %s, height = %s WHERE id = %s",
        (key, content_type, len(body), width, height, media_id),
    )
    return key


@pytest.fixture
async def media_ids(database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID]) -> list[UUID]:
    await add_article(database, trt_feed, images=3)
    return [row[0] for row in admin.execute("SELECT id FROM media ORDER BY id").fetchall()]


async def test_downloaded_images_are_converted_in_place(
    database: Database,
    admin: psycopg.Connection,
    storage: ObjectStorage,
    storage_client: S3Client,
    media_ids: list[UUID],
) -> None:
    """Çevrilmemiş görseller MinIO'dan okunur, WebP'ye çevrilir, aynı anahtara yazılır; satırları güncellenir."""
    jpeg_key = store_downloaded(admin, storage_client, media_ids[0], make_image("JPEG", (3200, 2400)), "image/jpeg")
    png_key = store_downloaded(admin, storage_client, media_ids[1], make_image("PNG", (800, 600)), "image/png")

    summary = await convert_media.MediaConverter(database, MediaRepository(), storage).run()

    assert (summary.converted, summary.failed) == (2, 0)
    assert summary.bytes_after < summary.bytes_before
    rows = admin.execute(
        "SELECT storage_key, content_type, width, height, size_bytes FROM media WHERE status = 'DOWNLOADED' ORDER BY id"
    ).fetchall()
    assert [row[:4] for row in rows] == [(jpeg_key, "image/webp", 1600, 1200), (png_key, "image/webp", 800, 600)]
    stored = storage_client.get_object(Bucket=MEDIA_BUCKET, Key=jpeg_key)
    body = stored["Body"].read()
    assert stored["ContentType"] == "image/webp"
    assert len(body) == rows[0][4]
    assert Image.open(io.BytesIO(body)).format == "WEBP"


async def test_already_converted_and_pending_images_are_left_alone(
    database: Database,
    admin: psycopg.Connection,
    storage: ObjectStorage,
    storage_client: S3Client,
    media_ids: list[UUID],
) -> None:
    """Zaten ortak biçimde olan ve henüz indirilmemiş görsellere dokunulmaz; komut tekrar çalıştırılabilir."""
    store_downloaded(admin, storage_client, media_ids[0], make_image("WEBP", (400, 300)), "image/webp")
    store_downloaded(admin, storage_client, media_ids[1], make_image("JPEG", (400, 300)), "image/jpeg")
    converter = convert_media.MediaConverter(database, MediaRepository(), storage)

    first = await converter.run()
    second = await converter.run()

    assert first.converted == 1
    assert second.converted == 0
    assert admin.execute("SELECT status FROM media WHERE id = %s", (media_ids[2],)).fetchone() == ("PENDING",)


async def test_file_that_cannot_be_converted_stays_as_it_is(
    database: Database,
    admin: psycopg.Connection,
    storage: ObjectStorage,
    storage_client: S3Client,
    media_ids: list[UUID],
) -> None:
    """Çevrilemeyen dosya olduğu gibi kalır ve sayılır; diğer görseller çevrilmeye devam eder."""
    broken_key = store_downloaded(
        admin, storage_client, media_ids[0], make_image("JPEG")[:100], "image/jpeg", size=(40, 30)
    )
    store_downloaded(admin, storage_client, media_ids[1], make_image("JPEG", (400, 300)), "image/jpeg")

    summary = await convert_media.MediaConverter(database, MediaRepository(), storage, page_size=1).run()

    assert (summary.converted, summary.failed) == (1, 1)
    assert admin.execute("SELECT content_type FROM media WHERE id = %s", (media_ids[0],)).fetchone() == ("image/jpeg",)
    assert storage_client.get_object(Bucket=MEDIA_BUCKET, Key=broken_key)["ContentType"] == "image/jpeg"


async def test_command_uses_the_configured_stores(
    settings: Settings,
    minio_url: str,
    admin: psycopg.Connection,
    storage_client: S3Client,
    media_ids: list[UUID],
) -> None:
    """Komutun giriş noktası, ayarlardaki PostgreSQL ve MinIO ile çalışır."""
    store_downloaded(admin, storage_client, media_ids[0], make_image("PNG", (300, 200)), "image/png")

    summary = await convert_media.run(replace(settings, minio_url=minio_url))

    assert summary.converted == 1


def test_command_exits_with_error_code_when_password_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Şifre tanımlı değilse komut hata koduyla çıkar."""
    monkeypatch.delenv("DB_PASSWORD", raising=False)

    with pytest.raises(SystemExit) as exit_info:
        convert_media.main()

    assert exit_info.value.code == 2
