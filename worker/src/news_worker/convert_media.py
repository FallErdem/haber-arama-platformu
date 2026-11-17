"""Daha önce indirilmiş görsellerin ortak biçime (WebP, en fazla 1600 piksel) çevrilmesi.

Yeni görseller indirilirken zaten çevrilir (`MediaDownloader`). Bu komut, bu kural gelmeden önce
indirilmiş görseller için bir kez çalıştırılır; çalışan işçinin içinden:

    kubectl exec -n haber deploy/worker -- news-worker-convert-media

Görseller kaynaktan yeniden indirilmez: MinIO'dan okunur, çevrilir ve aynı anahtarın üzerine yazılır.
Tekrar çalıştırılabilir; zaten çevrilmiş görsellere dokunmaz. İndirme döngüsüyle çakışmaz: o yalnızca
bekleyen görsellere, bu komut yalnızca indirilmiş görsellere dokunur.
"""

import asyncio
import logging
from dataclasses import dataclass

from news_worker.config import ConfigurationError, Settings
from news_worker.database import Database
from news_worker.image_converter import MAX_DIMENSION, OUTPUT_CONTENT_TYPE, convert_to_webp
from news_worker.image_downloader import NotAnImageError
from news_worker.logging_config import configure_logging
from news_worker.media import MediaRepository, StoredMedia
from news_worker.object_storage import ObjectStorage, StorageUnavailableError, create_storage_client

log = logging.getLogger(__name__)

PAGE_SIZE = 100


@dataclass(frozen=True)
class ConversionSummary:
    converted: int
    # Çevrilemeyen görseller olduğu gibi kalır; adresleri loga yazılır.
    failed: int
    bytes_before: int
    bytes_after: int


class MediaConverter:
    def __init__(
        self,
        database: Database,
        media_repository: MediaRepository,
        storage: ObjectStorage,
        page_size: int = PAGE_SIZE,
    ) -> None:
        self._database = database
        self._media_repository = media_repository
        self._storage = storage
        self._page_size = page_size

    async def run(self) -> ConversionSummary:
        """Ortak biçimde olmayan bütün indirilmiş görselleri çevirir.

        Nesne depolamaya ulaşılamazsa `StorageUnavailableError` fırlatır; o ana kadar çevrilenler kalır,
        komut yeniden çalıştırılınca kalanlardan devam eder.
        """
        converted = failed = bytes_before = bytes_after = 0
        after_id = None
        while True:
            async with await self._database.connect() as connection:
                page = await self._media_repository.find_unconverted(
                    connection, OUTPUT_CONTENT_TYPE, MAX_DIMENSION, after_id, self._page_size
                )
            if not page:
                break
            for media in page:
                result = await self._convert(media)
                if result is None:
                    failed += 1
                else:
                    converted += 1
                    bytes_before += result[0]
                    bytes_after += result[1]
            after_id = page[-1].id
            log.info("Görseller dönüştürülüyor: %d dönüştürüldü, %d dönüştürülemedi", converted, failed)
        return ConversionSummary(converted, failed, bytes_before, bytes_after)

    async def _convert(self, media: StoredMedia) -> tuple[int, int] | None:
        """Tek bir görseli çevirir; önceki ve sonraki boyutu döner. Çevrilemezse None."""
        original = await self._storage.get(media.storage_key)
        try:
            image = await asyncio.to_thread(convert_to_webp, original)
        except NotAnImageError as error:
            log.warning("Görsel dönüştürülemedi, olduğu gibi kaldı: %s (%s)", media.storage_key, error)
            return None
        await self._storage.put(media.storage_key, image.body, image.content_type)
        async with await self._database.connect() as connection:
            await self._media_repository.record_converted(
                connection, media.id, image.content_type, len(image.body), image.width, image.height
            )
        return len(original), len(image.body)


async def run(settings: Settings) -> ConversionSummary:
    storage = ObjectStorage(
        create_storage_client(
            settings.minio_url, settings.minio_access_key, settings.minio_secret_key, settings.http_timeout_seconds
        ),
        settings.media_bucket,
    )
    return await MediaConverter(Database(settings), MediaRepository(), storage).run()


def main() -> None:
    configure_logging()
    try:
        settings = Settings.from_environment()
    except ConfigurationError as error:
        log.error("Yapılandırma hatası: %s", error)
        raise SystemExit(2) from None
    try:
        summary = asyncio.run(run(settings))
    except StorageUnavailableError as error:
        log.error("Nesne depolamaya ulaşılamadı; komut yeniden çalıştırılabilir: %s", error)
        raise SystemExit(1) from None
    log.info(
        "Görsel dönüştürme bitti (dönüştürülen: %d, dönüştürülemeyen: %d, önce: %.1f MB, sonra: %.1f MB)",
        summary.converted,
        summary.failed,
        summary.bytes_before / 1_048_576,
        summary.bytes_after / 1_048_576,
    )
