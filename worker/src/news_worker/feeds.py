"""`feeds` tablosunun sorguları. Servisler SQL görmez; SQL yalnızca buradadır."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import psycopg
from psycopg.rows import TupleRow, class_row


@dataclass(frozen=True)
class DueFeed:
    """Okuma zamanı gelmiş bir besleme."""

    id: UUID
    source_code: str
    name: str
    url: str
    next_fetch_at: datetime


# Elle toplama da bu sorguyla çalışır: API beslemenin next_fetch_at değerini
# şimdiye çeker, işçi bir sonraki turda onu burada bulur (ADR-0013).
_FIND_DUE_QUERY = """
    SELECT f.id, s.code AS source_code, f.name, f.url, f.next_fetch_at
    FROM feeds f
    JOIN sources s ON s.id = f.source_id
    WHERE f.enabled
      AND s.enabled
      AND f.next_fetch_at <= now()
    ORDER BY f.next_fetch_at, f.id
    LIMIT %(limit)s
"""


class FeedRepository:
    async def find_due(self, connection: psycopg.AsyncConnection[TupleRow], limit: int) -> list[DueFeed]:
        """Etkin bir kaynağa ait, etkin ve okuma zamanı gelmiş beslemeleri en çok bekleyenden başlayarak döner."""
        # class_row: her satırı, sütun adlarını alan adlarıyla eşleştirerek DueFeed'e çevirir.
        async with connection.cursor(row_factory=class_row(DueFeed)) as cursor:
            await cursor.execute(_FIND_DUE_QUERY, {"limit": limit})
            return await cursor.fetchall()
