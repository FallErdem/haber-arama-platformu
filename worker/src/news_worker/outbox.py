"""`outbox_events` tablosunun sorguları: Elasticsearch'e aktarılmayı bekleyen notlar (ADR-0012).

Bir not "şu haber arama indeksinde güncellenecek" der; haberin içeriğini taşımaz. Notları
`OutboxRelay` işler.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

import psycopg
from psycopg.rows import TupleRow, class_row


@dataclass(frozen=True)
class OutboxEvent:
    id: UUID
    article_id: UUID
    # Bu notun daha önce kaç kez denenip başarısız olduğu.
    attempts: int


# Bekleyen ve deneme zamanı gelmiş notlar. ORDER BY id: kimlik uuidv7'dir, yani oluşturulma
# sırasıyla artar; notlar yazıldıkları sırayla işlenir.
_FIND_DUE_QUERY = """
    SELECT id, article_id, attempts
    FROM outbox_events
    WHERE status = 'PENDING'
      AND (next_attempt_at IS NULL OR next_attempt_at <= now())
    ORDER BY id
    LIMIT %(limit)s
"""

_MARK_PROCESSED_QUERY = """
    UPDATE outbox_events
    SET status = 'PROCESSED', processed_at = now(), last_error = NULL
    WHERE id = ANY(%(event_ids)s::uuid[])
"""

# Not PENDING kalır; yalnızca bir sonraki deneme zamanı ileri alınır. Nottan vazgeçilmez.
_RECORD_FAILURE_QUERY = """
    UPDATE outbox_events
    SET attempts = attempts + 1,
        last_error = %(error)s,
        next_attempt_at = now() + make_interval(mins => %(retry_delay_minutes)s::integer)
    WHERE id = %(event_id)s
"""


class OutboxRepository:
    async def find_due(self, connection: psycopg.AsyncConnection[TupleRow], limit: int) -> list[OutboxEvent]:
        """Bekleyen ve zamanı gelmiş notları, en eskisinden başlayarak en fazla `limit` kadar döner."""
        async with connection.cursor(row_factory=class_row(OutboxEvent)) as cursor:
            await cursor.execute(_FIND_DUE_QUERY, {"limit": limit})
            return await cursor.fetchall()

    async def mark_processed(self, connection: psycopg.AsyncConnection[TupleRow], event_ids: Sequence[UUID]) -> None:
        await connection.execute(_MARK_PROCESSED_QUERY, {"event_ids": list(event_ids)})

    async def record_failure(
        self,
        connection: psycopg.AsyncConnection[TupleRow],
        event_id: UUID,
        error: str,
        retry_delay_minutes: int,
    ) -> None:
        await connection.execute(
            _RECORD_FAILURE_QUERY,
            {"event_id": event_id, "error": error, "retry_delay_minutes": retry_delay_minutes},
        )
