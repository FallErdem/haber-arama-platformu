"""Nesne depolama (MinIO): indirilen görsellerin saklandığı yer (ADR-0010, `05-veri-modeli.md` 6. bölüm).

MinIO, Amazon S3 ile aynı arayüzü sunar; bağlantı S3 istemcisi `boto3` ile kurulur. Böylece ileride
başka bir S3 uyumlu depolamaya geçilirse kod değişmez (R-35).
"""

import asyncio
from typing import TYPE_CHECKING, cast
from uuid import UUID

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

if TYPE_CHECKING:
    # Yalnızca tür denetimi içindir (mypy); çalışan işçide bu paket bulunmaz.
    from types_boto3_s3 import S3Client


class StorageUnavailableError(Exception):
    """Nesne depolamaya yazılamadı (erişilemiyor, yetki veya başka bir hata)."""


def storage_key_for(article_id: UUID, media_id: UUID) -> str:
    """Görselin anahtarı. Bir haberin bütün dosyaları aynı ön ek altındadır; haber silinirken
    ön ekle birlikte silinebilir (FG-YP-14)."""
    return f"articles/{article_id}/{media_id}"


def create_storage_client(url: str, access_key: str, secret_key: str, timeout_seconds: float) -> S3Client:
    client = boto3.client(
        "s3",
        endpoint_url=url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        # MinIO bölge kullanmaz, ama S3 imzası bir bölge adı ister.
        region_name="us-east-1",
        config=Config(
            signature_version="s3v4",
            # path: kova adı adresin yolunda (`http://minio:9000/media/...`). Varsayılan biçim kova adını
            # alan adına ekler (`media.minio`); küme içinde böyle bir ad yoktur.
            s3={"addressing_style": "path"},
            connect_timeout=timeout_seconds,
            read_timeout=timeout_seconds,
            # Yeniden denemeyi görsel kuyruğu yapar; istemci kendi başına tekrar etmez.
            retries={"max_attempts": 1, "mode": "standard"},
        ),
    )
    # boto3 istemcinin türünü bildirmez; tür denetimi için S3 istemcisi olduğu belirtilir.
    return cast("S3Client", client)


class ObjectStorage:
    def __init__(self, client: S3Client, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    async def get(self, key: str) -> bytes:
        """Dosyayı okur (görsellerin ortak biçime çevrilmesi için)."""

        def read() -> bytes:
            # Gövdenin türünü botocore bildirmez; okunan değer bayt dizisidir.
            content: bytes = self._client.get_object(Bucket=self._bucket, Key=key)["Body"].read()
            return content

        try:
            return await asyncio.to_thread(read)
        except (BotoCoreError, ClientError) as error:
            raise StorageUnavailableError(f"Nesne depolamadan okunamadı: {type(error).__name__}") from error

    async def put(self, key: str, body: bytes, content_type: str) -> None:
        """Dosyayı yükler; aynı anahtar varsa üzerine yazar (yeniden deneme güvenlidir).

        boto3 asyncio ile çalışmaz; yükleme ayrı bir iş parçacığında yapılır, diğer işler beklemez.
        """
        try:
            await asyncio.to_thread(
                self._client.put_object, Bucket=self._bucket, Key=key, Body=body, ContentType=content_type
            )
        except (BotoCoreError, ClientError) as error:
            raise StorageUnavailableError(f"Nesne depolamaya yazılamadı: {type(error).__name__}") from error
