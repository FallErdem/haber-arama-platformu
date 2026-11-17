"""`media` tablosunun sorguları. Tablo aynı zamanda görsel indirme kuyruğudur (ADR-0013, 5. bölüm).

Haber kaydedilirken görselleri `PENDING` olarak yazılır; `MediaDownloader` zamanı gelenleri indirir
ve sonucu buraya yazar.
"""

from dataclasses import dataclass
from uuid import UUID

import psycopg
from psycopg.rows import TupleRow, class_row


@dataclass(frozen=True)
class PendingMedia:
    """İndirilmeyi bekleyen bir görsel; indirmek için gereken kaynak ayarlarıyla birlikte."""

    id: UUID
    article_id: UUID
    source_url: str
    # Daha önce kaç kez denenip başarısız olduğu.
    attempts: int
    # Görsel de kaynağın istek kurallarına tabidir (FG-VT-14): istek sırası kaynak koduyla alınır.
    source_code: str
    request_interval_seconds: int


@dataclass(frozen=True)
class StoredImage:
    """İndirilip nesne depolamaya yüklenmiş görselin bilgileri."""

    storage_key: str
    content_type: str
    size_bytes: int
    width: int
    height: int


# Devre dışı bırakılmış kaynağın görselleri indirilmez: kaynak kapatıldıysa ona istek de atılmaz.
# Sıra: en uzun süredir bekleyen önce; aynı haberin ana görseli (position 0) önce.
_FIND_DUE_QUERY = """
    SELECT m.id, m.article_id, m.source_url, m.attempts, s.code AS source_code, s.request_interval_seconds
    FROM media m
    JOIN articles a ON a.id = m.article_id
    JOIN sources s ON s.id = a.source_id
    WHERE m.status = 'PENDING'
      AND (m.next_attempt_at IS NULL OR m.next_attempt_at <= now())
      AND s.enabled
    ORDER BY m.next_attempt_at, m.article_id, m.position
    LIMIT %(limit)s
"""

_RECORD_DOWNLOADED_QUERY = """
    UPDATE media
    SET status = 'DOWNLOADED',
        storage_key = %(storage_key)s,
        content_type = %(content_type)s,
        size_bytes = %(size_bytes)s,
        width = %(width)s,
        height = %(height)s,
        attempts = attempts + 1,
        next_attempt_at = NULL,
        last_error = NULL
    WHERE id = %(media_id)s
"""

# Görsel PENDING kalır; bir sonraki deneme zamanı ileri alınır.
_RECORD_RETRY_QUERY = """
    UPDATE media
    SET attempts = attempts + 1,
        last_error = %(error)s,
        next_attempt_at = now() + make_interval(mins => %(retry_delay_minutes)s::integer)
    WHERE id = %(media_id)s
"""

# Bir daha denenmez; haberde yer tutucu gösterilir (FG-AR-08).
_RECORD_FAILED_QUERY = """
    UPDATE media
    SET status = 'FAILED',
        attempts = attempts + 1,
        last_error = %(error)s,
        next_attempt_at = NULL
    WHERE id = %(media_id)s
"""


class MediaRepository:
    async def find_due(self, connection: psycopg.AsyncConnection[TupleRow], limit: int) -> list[PendingMedia]:
        """İndirilmeyi bekleyen ve deneme zamanı gelmiş görseller, en fazla `limit` kadar."""
        async with connection.cursor(row_factory=class_row(PendingMedia)) as cursor:
            await cursor.execute(_FIND_DUE_QUERY, {"limit": limit})
            return await cursor.fetchall()

    async def record_downloaded(
        self, connection: psycopg.AsyncConnection[TupleRow], media_id: UUID, image: StoredImage
    ) -> None:
        await connection.execute(
            _RECORD_DOWNLOADED_QUERY,
            {
                "media_id": media_id,
                "storage_key": image.storage_key,
                "content_type": image.content_type,
                "size_bytes": image.size_bytes,
                "width": image.width,
                "height": image.height,
            },
        )

    async def record_retry(
        self, connection: psycopg.AsyncConnection[TupleRow], media_id: UUID, error: str, retry_delay_minutes: int
    ) -> None:
        await connection.execute(
            _RECORD_RETRY_QUERY, {"media_id": media_id, "error": error, "retry_delay_minutes": retry_delay_minutes}
        )

    async def record_failed(self, connection: psycopg.AsyncConnection[TupleRow], media_id: UUID, error: str) -> None:
        await connection.execute(_RECORD_FAILED_QUERY, {"media_id": media_id, "error": error})
