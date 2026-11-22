"""Bakım işi: haberlerin yaşam döngüsü durumunu günceller ve eski yardımcı kayıtları siler.

1. Yaşam döngüsü (ADR-0011): yayın tarihi 30 günden yeni haber HOT, 30 gün ile 1 yıl arası WARM, daha eskisi
   COLD. İşçi haberi kaydederken durumu doğru verir; burada yalnızca zamanla yaşlanan haberler güncellenir.
   Durum yalnızca PostgreSQL'dedir, arama indeksine bir şey yazılmaz.
2. Temizlik: saklama süresi dolan işlenmiş outbox notları, toplama kayıtları ve besleme testleri silinir.
   Haberlerin kendisi silinmez.

İş, işçi açılınca bir kez, sonra 12 saatte bir çalışır. Her işlem 1000'erli parçalarla yapılır: çok sayıda
satır olduğunda tablo uzun süre kilitlenmez.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import psycopg
from psycopg.rows import TupleRow

from news_worker.database import Database, wait_for_stop

log = logging.getLogger(__name__)

BATCH_SIZE = 1000

# Bir parçalık iş: bağlantıyı alır, değişen satır sayısını döner.
type _Batch = Callable[[psycopg.AsyncConnection[TupleRow]], Awaitable[int]]


@dataclass(frozen=True)
class RetentionPeriods:
    """Saklama süreleri (gün): bu kadar günden eski kayıtlar silinir."""

    outbox_days: int
    ingestion_run_days: int
    feed_test_days: int


@dataclass(frozen=True)
class MaintenanceResult:
    """Bir turda değişen satır sayıları."""

    became_warm: int
    became_cold: int
    deleted_outbox_events: int
    deleted_ingestion_runs: int
    deleted_feed_tests: int


# Her sorgu en fazla %(limit)s satıra dokunur; çağıran, sayı sınırdan küçük gelene kadar tekrarlar.
# PostgreSQL UPDATE ve DELETE'te LIMIT kabul etmez; satırlar önce bir alt sorguyla seçilir.

# Bir yıldan eski haber COLD olur (HOT veya WARM olsun). Önce bu çalışır: bir yıldır güncellenmemiş bir HOT
# haber doğrudan COLD olur, arada WARM yapılmaz.
_MAKE_COLD_QUERY = """
    UPDATE articles SET lifecycle_state = 'COLD'
    WHERE id IN (
        SELECT id FROM articles
        WHERE lifecycle_state IN ('HOT', 'WARM') AND published_at <= now() - interval '1 year'
        LIMIT %(limit)s
    )
"""

# 30 günden eski HOT haber WARM olur. (lifecycle_state, published_at) indeksini kullanır.
_MAKE_WARM_QUERY = """
    UPDATE articles SET lifecycle_state = 'WARM'
    WHERE id IN (
        SELECT id FROM articles
        WHERE lifecycle_state = 'HOT' AND published_at <= now() - interval '30 days'
        LIMIT %(limit)s
    )
"""

# Yalnızca işlenmiş notlar silinir; bekleyen nota (henüz aktarılmamış değişiklik) hiç dokunulmaz.
# processed_at'te indeks yoktur: işlenmiş notlar birkaç gün tutulduğu için tablo hep küçüktür.
_DELETE_OUTBOX_EVENTS_QUERY = """
    DELETE FROM outbox_events
    WHERE id IN (
        SELECT id FROM outbox_events
        WHERE status = 'PROCESSED' AND processed_at < now() - make_interval(days => %(days)s)
        LIMIT %(limit)s
    )
"""

_DELETE_INGESTION_RUNS_QUERY = """
    DELETE FROM ingestion_runs
    WHERE id IN (
        SELECT id FROM ingestion_runs
        WHERE started_at < now() - make_interval(days => %(days)s)
        LIMIT %(limit)s
    )
"""

_DELETE_FEED_TESTS_QUERY = """
    DELETE FROM feed_tests
    WHERE id IN (
        SELECT id FROM feed_tests
        WHERE created_at < now() - make_interval(days => %(days)s)
        LIMIT %(limit)s
    )
"""


class MaintenanceRepository:
    async def make_cold(self, connection: psycopg.AsyncConnection[TupleRow], limit: int) -> int:
        cursor = await connection.execute(_MAKE_COLD_QUERY, {"limit": limit})
        return cursor.rowcount

    async def make_warm(self, connection: psycopg.AsyncConnection[TupleRow], limit: int) -> int:
        cursor = await connection.execute(_MAKE_WARM_QUERY, {"limit": limit})
        return cursor.rowcount

    async def delete_outbox_events(self, connection: psycopg.AsyncConnection[TupleRow], days: int, limit: int) -> int:
        cursor = await connection.execute(_DELETE_OUTBOX_EVENTS_QUERY, {"days": days, "limit": limit})
        return cursor.rowcount

    async def delete_ingestion_runs(self, connection: psycopg.AsyncConnection[TupleRow], days: int, limit: int) -> int:
        cursor = await connection.execute(_DELETE_INGESTION_RUNS_QUERY, {"days": days, "limit": limit})
        return cursor.rowcount

    async def delete_feed_tests(self, connection: psycopg.AsyncConnection[TupleRow], days: int, limit: int) -> int:
        cursor = await connection.execute(_DELETE_FEED_TESTS_QUERY, {"days": days, "limit": limit})
        return cursor.rowcount


class Maintenance:
    def __init__(
        self,
        database: Database,
        repository: MaintenanceRepository,
        retention: RetentionPeriods,
        interval_seconds: float,
        batch_size: int = BATCH_SIZE,
    ) -> None:
        self._database = database
        self._repository = repository
        self._retention = retention
        self._interval_seconds = interval_seconds
        self._batch_size = batch_size

    async def run_once(self, stop: asyncio.Event) -> MaintenanceResult:
        """Bir tur: önce yaşam döngüsü, sonra temizlik."""
        repository = self._repository
        retention = self._retention
        limit = self._batch_size
        return MaintenanceResult(
            became_cold=await self._repeat(stop, lambda c: repository.make_cold(c, limit)),
            became_warm=await self._repeat(stop, lambda c: repository.make_warm(c, limit)),
            deleted_outbox_events=await self._repeat(
                stop, lambda c: repository.delete_outbox_events(c, retention.outbox_days, limit)
            ),
            deleted_ingestion_runs=await self._repeat(
                stop, lambda c: repository.delete_ingestion_runs(c, retention.ingestion_run_days, limit)
            ),
            deleted_feed_tests=await self._repeat(
                stop, lambda c: repository.delete_feed_tests(c, retention.feed_test_days, limit)
            ),
        )

    async def _repeat(self, stop: asyncio.Event, batch: _Batch) -> int:
        """Bir parçalık işi, parça dolu gelmeyene kadar tekrarlar; her parça ayrı bir işlemdir (commit)."""
        total = 0
        while not stop.is_set():
            async with await self._database.connect() as connection:
                count = await batch(connection)
            total += count
            if count < self._batch_size:
                break
        return total

    async def run(self, stop: asyncio.Event) -> None:
        """İşçi açılınca bir tur yapar, sonra durdurma istenene kadar aralıkla tekrarlar."""
        while not stop.is_set():
            try:
                result = await self.run_once(stop)
                log.info(
                    "Bakım tamamlandı: %d haber WARM, %d haber COLD oldu; silinen: %d outbox notu, "
                    "%d toplama kaydı, %d besleme testi",
                    result.became_warm,
                    result.became_cold,
                    result.deleted_outbox_events,
                    result.deleted_ingestion_runs,
                    result.deleted_feed_tests,
                )
            except Exception:
                log.exception("Bakım turu başarısız oldu")
            await wait_for_stop(stop, self._interval_seconds)
