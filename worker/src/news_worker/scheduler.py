"""Zamanlayıcı döngüsü: belirli aralıklarla okuma zamanı gelmiş beslemeleri bulur."""

import asyncio
import logging
import time
from collections.abc import Callable

from news_worker.database import Database, wait_for_stop
from news_worker.feeds import FeedRepository

log = logging.getLogger(__name__)

# Son başarılı turun üzerinden bu kadar aralık geçtiyse zamanlayıcı sağlıksız sayılır.
_HEALTHY_WITHIN_INTERVALS = 3


class Scheduler:
    def __init__(
        self,
        database: Database,
        feed_repository: FeedRepository,
        interval_seconds: float,
        batch_size: int = 100,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._database = database
        self._feed_repository = feed_repository
        self._interval_seconds = interval_seconds
        self._batch_size = batch_size
        # Testlerde sahte bir saat verilebilir. monotonic: sistem saati değişse de geri gitmez.
        self._clock = clock
        self._last_successful_tick: float | None = None

    async def tick(self) -> int:
        """Tek bir tur: okuma zamanı gelmiş beslemeleri bulur ve sayısını döner.

        İskelette beslemeler yalnızca bulunur; okunmaları İ-10 ve İ-12'de eklenecek.
        """
        # Her turda yeni bağlantı: veritabanı yeniden başlasa bile sonraki tur kendiliğinden toparlanır.
        async with await self._database.connect() as connection:
            due_feeds = await self._feed_repository.find_due(connection, self._batch_size)
        log.info("Okuma zamanı gelmiş besleme sayısı: %d", len(due_feeds))
        self._last_successful_tick = self._clock()
        return len(due_feeds)

    async def run(self, stop: asyncio.Event) -> None:
        """Durdurma istenene kadar turları aralıklarla çalıştırır."""
        while not stop.is_set():
            try:
                await self.tick()
            except Exception:
                # Bir turdaki hata (örneğin veritabanına ulaşılamaması) işçiyi durdurmamalı.
                # Hata yığın iziyle loga yazılır ve bir sonraki turda yeniden denenir.
                log.exception("Zamanlayıcı turu başarısız oldu")
            await wait_for_stop(stop, self._interval_seconds)

    def is_healthy(self) -> bool:
        """Son başarılı tur yeterince yakınsa true döner; hazır olma kontrolü bunu kullanır."""
        if self._last_successful_tick is None:
            return False
        elapsed = self._clock() - self._last_successful_tick
        return elapsed <= self._interval_seconds * _HEALTHY_WITHIN_INTERVALS
