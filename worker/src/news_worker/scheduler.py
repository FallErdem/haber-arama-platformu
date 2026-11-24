"""Zamanlayıcı döngüsü: belirli aralıklarla okuma zamanı gelmiş beslemeleri bulur ve toplatır."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

from news_worker.database import Database, wait_for_stop
from news_worker.feeds import DueFeed, FeedRepository

log = logging.getLogger(__name__)

# Son canlılık işaretinin üzerinden bu kadar aralık geçtiyse zamanlayıcı sağlıksız sayılır.
# Varsayılan ayarlarla 90 saniyedir; tek bir beslemenin okunması en fazla istek aralığı (10 sn)
# artı toplam indirme süresi (30 sn) kadar sürebildiğinden bu eşik yeterlidir.
_HEALTHY_WITHIN_INTERVALS = 3


class Scheduler:
    def __init__(
        self,
        database: Database,
        feed_repository: FeedRepository,
        ingest: Callable[[DueFeed], Awaitable[None]],
        interval_seconds: float,
        batch_size: int = 100,
        clock: Callable[[], float] = time.monotonic,
        skipped_reader_types: frozenset[str] = frozenset(),
    ) -> None:
        self._database = database
        self._feed_repository = feed_repository
        # Bir beslemeyi toplayan fonksiyon (IngestionService.ingest). Testlerde sahtesi verilir.
        self._ingest = ingest
        self._interval_seconds = interval_seconds
        self._batch_size = batch_size
        # Okunamayacak okuyucu türleri (API anahtarı tanımlı değilse NYT); bu türlerin beslemeleri hiç seçilmez.
        self._skipped_reader_types = skipped_reader_types
        # Testlerde sahte bir saat verilebilir. monotonic: sistem saati değişse de geri gitmez.
        self._clock = clock
        self._last_alive_at: float | None = None

    async def tick(self, stop: asyncio.Event | None = None) -> int:
        """Tek bir tur: okuma zamanı gelmiş beslemeleri bulur, toplatır ve sayısını döner.

        Aynı kaynağın beslemeleri sırayla, farklı kaynaklar aynı anda okunur (ADR-0013).
        `stop` verilmişse ve durdurma istenmişse henüz başlanmamış beslemeler bu turda okunmaz.
        """
        # Her turda yeni bağlantı: veritabanı yeniden başlasa bile sonraki tur kendiliğinden toparlanır.
        async with await self._database.connect() as connection:
            due_feeds = await self._feed_repository.find_due(connection, self._batch_size, self._skipped_reader_types)
        self._mark_alive()
        log.info("Okuma zamanı gelmiş besleme sayısı: %d", len(due_feeds))

        feeds_by_source: dict[str, list[DueFeed]] = {}
        for feed in due_feeds:
            feeds_by_source.setdefault(feed.source_code, []).append(feed)
        # gather: her kaynağın beslemeleri ayrı bir görevde okunur; hepsi bitince tur biter.
        await asyncio.gather(*(self._ingest_source(feeds, stop) for feeds in feeds_by_source.values()))
        return len(due_feeds)

    async def _ingest_source(self, feeds: list[DueFeed], stop: asyncio.Event | None) -> None:
        """Bir kaynağın beslemelerini sırayla toplatır. Hata fırlatmaz."""
        for feed in feeds:
            if stop is not None and stop.is_set():
                return
            try:
                await self._ingest(feed)
            except Exception:
                # Bir beslemenin hatası ne aynı kaynağın sıradaki beslemelerini ne de diğer
                # kaynakları durdurur (FOG-08). Hata yığın iziyle loga yazılır.
                log.exception("Besleme toplanamadı: %s", feed.url)
                continue
            # Uzun süren bir turda da "hâlâ çalışıyorum" işareti güncel kalır.
            self._mark_alive()

    async def run(self, stop: asyncio.Event) -> None:
        """Durdurma istenene kadar turları aralıklarla çalıştırır."""
        while not stop.is_set():
            try:
                await self.tick(stop)
            except Exception:
                # Bir turdaki hata (örneğin veritabanına ulaşılamaması) işçiyi durdurmamalı.
                # Hata yığın iziyle loga yazılır ve bir sonraki turda yeniden denenir.
                log.exception("Zamanlayıcı turu başarısız oldu")
            await wait_for_stop(stop, self._interval_seconds)

    def is_healthy(self) -> bool:
        """Zamanlayıcı yakın zamanda iş yaptıysa true döner; hazır olma kontrolü bunu kullanır."""
        if self._last_alive_at is None:
            return False
        elapsed = self._clock() - self._last_alive_at
        return elapsed <= self._interval_seconds * _HEALTHY_WITHIN_INTERVALS

    def _mark_alive(self) -> None:
        self._last_alive_at = self._clock()
