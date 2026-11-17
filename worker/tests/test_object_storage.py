"""Nesne depolama testleri: gerçek MinIO (kümedekiyle aynı sürüm), işçinin kendi kullanıcısı ve politikasıyla."""

from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from conftest import MEDIA_BUCKET, STORAGE_WORKER_USER, make_image

from news_worker.object_storage import (
    ObjectStorage,
    StorageUnavailableError,
    create_storage_client,
    storage_key_for,
)

if TYPE_CHECKING:
    from types_boto3_s3 import S3Client

ARTICLE_ID = UUID("019a0000-0000-7000-8000-000000000001")
MEDIA_ID = UUID("019a0000-0000-7000-8000-0000000000aa")


def test_key_groups_files_under_their_article() -> None:
    """Anahtar haber kimliğiyle başlar; bir haberin bütün dosyaları aynı ön ek altındadır."""
    assert storage_key_for(ARTICLE_ID, MEDIA_ID) == (
        "articles/019a0000-0000-7000-8000-000000000001/019a0000-0000-7000-8000-0000000000aa"
    )


async def test_image_is_uploaded_with_its_content_type(storage: ObjectStorage, storage_client: S3Client) -> None:
    """Görsel kovaya yüklenir; içerik türü de saklanır (API görseli bu türle sunacak)."""
    body = make_image("PNG")
    key = storage_key_for(ARTICLE_ID, MEDIA_ID)

    await storage.put(key, body, "image/png")

    stored = storage_client.get_object(Bucket=MEDIA_BUCKET, Key=key)
    assert stored["Body"].read() == body
    assert stored["ContentType"] == "image/png"


async def test_uploading_again_overwrites_the_same_key(storage: ObjectStorage, storage_client: S3Client) -> None:
    """Aynı görsel yeniden yüklenirse ikinci bir dosya oluşmaz; yeniden deneme güvenlidir."""
    key = storage_key_for(ARTICLE_ID, MEDIA_ID)
    await storage.put(key, b"ilk", "image/jpeg")

    await storage.put(key, b"ikinci", "image/jpeg")

    listed = storage_client.list_objects_v2(Bucket=MEDIA_BUCKET, Prefix="articles/")
    assert [item["Key"] for item in listed["Contents"]] == [key]
    assert storage_client.get_object(Bucket=MEDIA_BUCKET, Key=key)["Body"].read() == b"ikinci"


async def test_worker_cannot_write_outside_its_bucket(minio_url: str, storage_client: S3Client) -> None:
    """İşçinin yetkisi yalnızca `media` kovasındadır; başka bir kovaya yazamaz."""
    other = ObjectStorage(storage_client, "baska-kova")

    # MinIO yetki hatasını kendi koduyla bildirir; hata metninde neden görünür.
    with pytest.raises(StorageUnavailableError, match="AccessDenied"):
        await other.put("dosya", b"x", "image/jpeg")


async def test_unreachable_storage_is_reported() -> None:
    """Nesne depolamaya ulaşılamazsa anlaşılır bir hata fırlatılır."""
    client = create_storage_client("http://127.0.0.1:9", STORAGE_WORKER_USER, "x", timeout_seconds=1)

    with pytest.raises(StorageUnavailableError, match="EndpointConnectionError"):
        await ObjectStorage(client, MEDIA_BUCKET).put("dosya", b"x", "image/jpeg")
