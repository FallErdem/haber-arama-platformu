"""Kaynak içeriğinin silinmesi (FG-YP-14; `05-veri-modeli.md` 4. bölüm).

Yönetici silmeyi API'den ister; API kaynağın `purge_requested_at` alanını doldurur. İşçi bu alanı dolu
kaynakları bulur ve haberlerini parça parça siler. Her parçada:

1. Önce haberlerin MinIO'daki görsel dosyaları silinir.
2. Sonra tek bir veritabanı işleminde haberler silinir ve her haber için Elasticsearch'teki belgesinin
   silinmesi için bir outbox notu (`DELETE`) yazılır. Haberin görsel, kategori ve kaydedilme satırları
   veritabanınca zincirleme silinir (`ON DELETE CASCADE`).

Sıranın nedeni: bir görselin MinIO'daki anahtarını (`storage_key`) yalnızca veritabanındaki `media` satırı
bilir. MinIO'daki görsel dosyası silinip veritabanındaki haber satırı silinemezse, satır anahtarı hâlâ
bildiği için haber bir sonraki turda yeniden ele alınır (olmayan dosyayı silmek hata değildir). Ters
sırada satır silinip dosya silinemeseydi anahtar da kaybolurdu; kimsenin bulup silemeyeceği sahipsiz
dosyalar MinIO'da birikirdi. İşçi yarıda dursa da silme bir sonraki turda kaldığı yerden devam eder.

Haber kalmayınca aynı işlemde istek boşaltılır ve audit'e `SOURCE_PURGED` yazılır.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import psycopg
from psycopg.rows import TupleRow, class_row

from news_worker.audit import AuditRepository
from news_worker.database import Database, wait_for_stop
from news_worker.object_storage import ObjectStorage, StorageUnavailableError

log = logging.getLogger(__name__)

PURGED_ACTION = "SOURCE_PURGED"


@dataclass(frozen=True)
class PurgeRequest:
    source_id: UUID
    code: str
    # Silmenin istendiği an; istek yalnızca bu değer değişmediyse boşaltılır.
    purge_requested_at: datetime


@dataclass(frozen=True)
class PurgeBatch:
    article_ids: list[UUID]
    # Bu haberlerin MinIO'daki dosyaları; yalnızca indirilmiş görsellerin anahtarı vardır.
    storage_keys: list[str]


# Silme isteği olan kaynaklar, en eski istek önce. Etkin kaynak silinmez: API silmeyi yalnızca devre dışı
# kaynakta kabul eder; etkin bir kaynakta silme sürerken yeni haber eklenebilirdi. Burada da denetlenir.
_FIND_REQUESTED_QUERY = """
    SELECT id AS source_id, code, purge_requested_at
    FROM sources
    WHERE purge_requested_at IS NOT NULL
      AND NOT enabled
    ORDER BY purge_requested_at
"""

_FIND_ARTICLES_QUERY = """
    SELECT id
    FROM articles
    WHERE source_id = %(source_id)s
    ORDER BY id
    LIMIT %(limit)s
"""

_FIND_STORAGE_KEYS_QUERY = """
    SELECT storage_key
    FROM media
    WHERE article_id = ANY(%(article_ids)s::uuid[])
      AND storage_key IS NOT NULL
"""

# media, article_categories ve saved_articles satırları zincirleme silinir (ON DELETE CASCADE).
_DELETE_ARTICLES_QUERY = """
    DELETE FROM articles
    WHERE id = ANY(%(article_ids)s::uuid[])
"""

# Notun article_id'si yabancı anahtar değildir; haber silindikten sonra da var olabilir. Aktarım haberi
# bulamayınca belgesini siler (outbox_relay).
_INSERT_DELETE_NOTES_QUERY = """
    INSERT INTO outbox_events (article_id, operation, status, next_attempt_at)
    SELECT article_id, 'DELETE', 'PENDING', now()
    FROM unnest(%(article_ids)s::uuid[]) AS article_id
"""

# İstek, yalnızca okunduğundan beri değişmediyse ve kaynağın haberi kalmadıysa boşaltılır.
_FINISH_QUERY = """
    UPDATE sources
    SET purge_requested_at = NULL
    WHERE id = %(source_id)s
      AND purge_requested_at = %(purge_requested_at)s
      AND NOT EXISTS (SELECT 1 FROM articles WHERE source_id = %(source_id)s)
"""


class SourcePurgeRepository:
    async def find_requested(self, connection: psycopg.AsyncConnection[TupleRow]) -> list[PurgeRequest]:
        async with connection.cursor(row_factory=class_row(PurgeRequest)) as cursor:
            await cursor.execute(_FIND_REQUESTED_QUERY)
            return await cursor.fetchall()

    async def find_batch(
        self, connection: psycopg.AsyncConnection[TupleRow], source_id: UUID, limit: int
    ) -> PurgeBatch:
        """Kaynağın en fazla `limit` haberi ve bu haberlerin dosya anahtarları."""
        cursor = await connection.execute(_FIND_ARTICLES_QUERY, {"source_id": source_id, "limit": limit})
        article_ids = [row[0] for row in await cursor.fetchall()]
        if not article_ids:
            return PurgeBatch(article_ids=[], storage_keys=[])
        cursor = await connection.execute(_FIND_STORAGE_KEYS_QUERY, {"article_ids": article_ids})
        return PurgeBatch(article_ids=article_ids, storage_keys=[row[0] for row in await cursor.fetchall()])

    async def delete_articles(self, connection: psycopg.AsyncConnection[TupleRow], article_ids: list[UUID]) -> int:
        """Haberleri siler ve belgelerinin silinmesi için outbox notlarını yazar; silinen haber sayısını döner.

        Çağıranın aynı işlemde (tek bağlantı bloğunda) çağırması gerekir: haber silinip not yazılamazsa
        belge arama indeksinde kalırdı.
        """
        cursor = await connection.execute(_DELETE_ARTICLES_QUERY, {"article_ids": article_ids})
        await connection.execute(_INSERT_DELETE_NOTES_QUERY, {"article_ids": article_ids})
        return cursor.rowcount

    async def finish(self, connection: psycopg.AsyncConnection[TupleRow], request: PurgeRequest) -> bool:
        """Silme isteğini boşaltır; boşalttıysa `True`."""
        cursor = await connection.execute(
            _FINISH_QUERY,
            {"source_id": request.source_id, "purge_requested_at": request.purge_requested_at},
        )
        return cursor.rowcount == 1


class SourcePurger:
    def __init__(
        self,
        database: Database,
        repository: SourcePurgeRepository,
        audit_repository: AuditRepository,
        storage: ObjectStorage,
        interval_seconds: float,
        batch_size: int,
    ) -> None:
        self._database = database
        self._repository = repository
        self._audit_repository = audit_repository
        self._storage = storage
        self._interval_seconds = interval_seconds
        self._batch_size = batch_size

    async def purge_requested(self, stop: asyncio.Event) -> None:
        """Silme isteği olan bütün kaynakları siler (bir tur)."""
        async with await self._database.connect() as connection:
            requests = await self._repository.find_requested(connection)
        for request in requests:
            if stop.is_set():
                return
            await self._purge(request, stop)

    async def _purge(self, request: PurgeRequest, stop: asyncio.Event) -> None:
        # Sayılar bu turda silinenlerdir. İşçi yarıda yeniden başladıysa önceki turda silinenler sayılmaz.
        article_count = 0
        media_count = 0
        while not stop.is_set():
            async with await self._database.connect() as connection:
                batch = await self._repository.find_batch(connection, request.source_id, self._batch_size)
            if not batch.article_ids:
                break
            # Önce dosyalar; silinemezse hata yükselir, satırlara dokunulmaz.
            await self._storage.delete_many(batch.storage_keys)
            # Sonra satırlar ve notlar, tek işlemde.
            async with await self._database.connect() as connection:
                article_count += await self._repository.delete_articles(connection, batch.article_ids)
            media_count += len(batch.storage_keys)
            log.info("%s kaynağından %d haber silindi", request.code, len(batch.article_ids))
        else:
            # Durdurma istendi: silme bir sonraki çalışmada kaldığı yerden sürer.
            return

        async with await self._database.connect() as connection:
            if await self._repository.finish(connection, request):
                await self._audit_repository.insert_system_event(
                    connection,
                    PURGED_ACTION,
                    "SOURCE",
                    request.source_id,
                    {"article_count": article_count, "media_count": media_count},
                )
                log.info(
                    "%s kaynağının içeriği silindi: %d haber, %d görsel dosyası",
                    request.code,
                    article_count,
                    media_count,
                )

    async def run(self, stop: asyncio.Event) -> None:
        """Durdurma istenene kadar silme isteklerine bakar."""
        while not stop.is_set():
            try:
                await self.purge_requested(stop)
            except StorageUnavailableError as error:
                # MinIO'ya ulaşılamıyor: satırlar silinmedi, bir sonraki turda yeniden denenir.
                log.warning("Görsel dosyaları silinemedi; içerik silme bekliyor: %s", error)
            except Exception:
                log.exception("İçerik silme turu başarısız oldu")
            await wait_for_stop(stop, self._interval_seconds)
