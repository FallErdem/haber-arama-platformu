"""Görsel indirme döngüsü: kuyruktaki görselleri indirir, doğrular, WebP'ye çevirir ve nesne depolamaya yükler
(ADR-0013, 5. bölüm; FG-VT-14).

Aynı kaynağın görselleri sırayla, farklı kaynaklarınki aynı anda indirilir. Görsel istekleri besleme
okumalarıyla aynı istek sınırlayıcısını kullanır; kaynağa giden toplam istek sıklığı sınırı aşmaz.
"""

import asyncio
import logging
from collections import Counter
from enum import StrEnum

from news_worker.database import Database, wait_for_stop
from news_worker.image_converter import convert_to_webp
from news_worker.image_downloader import DownloadFailed, ImageDownloader, NotAnImageError
from news_worker.media import MediaRepository, PendingMedia, StoredImage
from news_worker.object_storage import ObjectStorage, StorageUnavailableError, storage_key_for
from news_worker.rate_limiter import SourceRateLimiter

log = logging.getLogger(__name__)

# Geçici hatalarda yeniden deneme: 1., 2. ve 3. hatadan sonra 1, 5 ve 15 dakika, 4. hatadan sonra
# yine 15 dakika; 5. hatada görsel FAILED olur. Beslemelerdeki kuralın aynısıdır (ADR-0017, 10. bölüm).
MAX_ATTEMPTS = 5
RETRY_DELAYS_MINUTES = (1, 5, 15)

_MAX_ERROR_LENGTH = 500


class Outcome(StrEnum):
    """Bir görselin bu turdaki sonucu; turun özet log satırında sayılır."""

    DOWNLOADED = "DOWNLOADED"
    RETRY = "RETRY"
    FAILED = "FAILED"


def retry_delay_minutes(attempts: int) -> int:
    """Daha önce `attempts` kez başarısız olmuş bir görselin bir sonraki denemesine kaç dakika var."""
    return RETRY_DELAYS_MINUTES[min(attempts, len(RETRY_DELAYS_MINUTES) - 1)]


class MediaDownloader:
    def __init__(
        self,
        database: Database,
        media_repository: MediaRepository,
        image_downloader: ImageDownloader,
        storage: ObjectStorage,
        rate_limiter: SourceRateLimiter,
        interval_seconds: float,
        batch_size: int,
    ) -> None:
        self._database = database
        self._media_repository = media_repository
        self._image_downloader = image_downloader
        self._storage = storage
        self._rate_limiter = rate_limiter
        self._interval_seconds = interval_seconds
        self._batch_size = batch_size

    async def download_batch(self, stop: asyncio.Event | None = None) -> int:
        """Bir grup görseli işler ve gruptaki görsel sayısını döner.

        Nesne depolamaya yazılamazsa `StorageUnavailableError` fırlatır: sorun görselde değil, o
        turda kalan görsellere dokunulmaz ve bir sonraki turda yeniden denenirler.
        """
        async with await self._database.connect() as connection:
            due = await self._media_repository.find_due(connection, self._batch_size)
        if not due:
            return 0
        by_source: dict[str, list[PendingMedia]] = {}
        for media in due:
            by_source.setdefault(media.source_code, []).append(media)
        results = await asyncio.gather(*(self._download_source(items, stop) for items in by_source.values()))

        outcomes = Counter(outcome for source_outcomes in results for outcome in source_outcomes)
        log.info(
            "Görseller işlendi (indirilen: %d, yeniden denenecek: %d, başarısız: %d)",
            outcomes[Outcome.DOWNLOADED],
            outcomes[Outcome.RETRY],
            outcomes[Outcome.FAILED],
        )
        return len(due)

    async def run(self, stop: asyncio.Event) -> None:
        """Durdurma istenene kadar görselleri indirir."""
        while not stop.is_set():
            try:
                count = await self.download_batch(stop)
            except StorageUnavailableError as error:
                log.warning("Nesne depolamaya ulaşılamadı; görseller bekliyor: %s", error.__cause__ or error)
                count = 0
            except Exception:
                log.exception("Görsel indirme turu başarısız oldu")
                count = 0
            # Grup dolu geldiyse bekleyen başka görseller de vardır; beklemeden devam edilir.
            if count < self._batch_size:
                await wait_for_stop(stop, self._interval_seconds)

    async def _download_source(self, items: list[PendingMedia], stop: asyncio.Event | None) -> list[Outcome]:
        outcomes: list[Outcome] = []
        for media in items:
            if stop is not None and stop.is_set():
                break
            outcomes.append(await self._download(media))
        return outcomes

    async def _download(self, media: PendingMedia) -> Outcome:
        async with self._rate_limiter.request_slot(media.source_code, media.request_interval_seconds):
            result = await self._image_downloader.download(media.source_url)

        if isinstance(result, DownloadFailed):
            return await self._record_failure(media, result)
        try:
            # Ortak biçime çevirme işlemciyi kullanır; ayrı bir iş parçacığında yapılır ki diğer işler beklemesin.
            image = await asyncio.to_thread(convert_to_webp, result.body)
        except NotAnImageError as error:
            return await self._record_failure(media, DownloadFailed(str(error), permanent=True))

        key = storage_key_for(media.article_id, media.id)
        # Yükleme başarılı olup satır güncellenemezse görsel bir sonraki turda yeniden indirilir ve
        # aynı anahtarın üzerine yazılır; sonuç değişmez.
        await self._storage.put(key, image.body, image.content_type)
        stored = StoredImage(
            storage_key=key,
            content_type=image.content_type,
            size_bytes=len(image.body),
            width=image.width,
            height=image.height,
        )
        async with await self._database.connect() as connection:
            await self._media_repository.record_downloaded(connection, media.id, stored)
        return Outcome.DOWNLOADED

    async def _record_failure(self, media: PendingMedia, failure: DownloadFailed) -> Outcome:
        error = failure.message[:_MAX_ERROR_LENGTH]
        attempts = media.attempts + 1
        async with await self._database.connect() as connection:
            if failure.permanent or attempts >= MAX_ATTEMPTS:
                log.warning("Görsel indirilemedi, bir daha denenmeyecek: %s (%s)", media.source_url, error)
                await self._media_repository.record_failed(connection, media.id, error)
                return Outcome.FAILED
            await self._media_repository.record_retry(connection, media.id, error, retry_delay_minutes(media.attempts))
            return Outcome.RETRY
