"""`ingestion_runs` tablosunun sorguları: her besleme okumasının kaydı (FG-VT-10)."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

import psycopg
from psycopg.rows import TupleRow


class RunTrigger(StrEnum):
    """`ingestion_runs.trigger`: okumayı zamanlayıcı mı başlattı, yönetici mi istedi (FG-YP-08)."""

    SCHEDULED = "SCHEDULED"
    MANUAL = "MANUAL"


class RunStatus(StrEnum):
    """`ingestion_runs.status` sütununun, okuma bittiğinde alabildiği değerler."""

    SUCCEEDED = "SUCCEEDED"
    NOT_MODIFIED = "NOT_MODIFIED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class RunResult:
    status: RunStatus
    http_status: int | None = None
    # Yönlendirmeler takip edildikten sonra varılan adres.
    final_url: str | None = None
    # Beslemede gelen haber sayısı = yeni + tekrar eden + atlanan.
    items_received: int | None = None
    items_new: int | None = None
    items_duplicate: int | None = None
    # Zorunlu alanı eksik olduğu veya kaydedilemediği için atlanan haberler.
    items_failed: int | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class RecentRequests:
    """Bir kaynağa son 24 saatte atılan istekler (günlük istek bütçesi, ADR-0009)."""

    count: int
    # En eski isteğin üzerinden 24 saat geçmesine, yani yeni bir istek hakkı açılmasına kalan süre; istek yoksa None.
    seconds_until_next_slot: float | None


_START_QUERY = """
    INSERT INTO ingestion_runs (feed_id, trigger, status, started_at)
    VALUES (%(feed_id)s, %(trigger)s, 'RUNNING', now())
    RETURNING id
"""

_FINISH_QUERY = """
    UPDATE ingestion_runs
    SET status = %(status)s,
        finished_at = now(),
        http_status = %(http_status)s,
        final_url = %(final_url)s,
        items_received = %(items_received)s,
        items_new = %(items_new)s,
        items_duplicate = %(items_duplicate)s,
        items_failed = %(items_failed)s,
        error_message = %(error_message)s
    WHERE id = %(run_id)s
"""

# Her okuma kaynağa atılmış bir istek sayılır (değişmedi ve başarısız okumalar dahil). Sayım takvim gününe göre
# değil, son 24 saate göre yapılır (mimari 7. bölüm); (feed_id, started_at) indeksi kullanılır.
_COUNT_RECENT_REQUESTS_QUERY = """
    SELECT count(*), extract(epoch FROM min(r.started_at) + interval '24 hours' - now())::double precision
    FROM ingestion_runs r
    JOIN feeds f ON f.id = r.feed_id
    WHERE f.source_id = %(source_id)s
      AND r.started_at > now() - interval '24 hours'
"""


class IngestionRunRepository:
    async def count_recent_requests(
        self, connection: psycopg.AsyncConnection[TupleRow], source_id: UUID
    ) -> RecentRequests:
        """Kaynağın bütün beslemelerine son 24 saatte atılan istekleri sayar."""
        cursor = await connection.execute(_COUNT_RECENT_REQUESTS_QUERY, {"source_id": source_id})
        row = await cursor.fetchone()
        assert row is not None  # count(*) her zaman bir satır döner.
        return RecentRequests(count=row[0], seconds_until_next_slot=row[1])

    async def start(self, connection: psycopg.AsyncConnection[TupleRow], feed_id: UUID, trigger: RunTrigger) -> UUID:
        """Okumanın başladığını kaydeder ve kaydın kimliğini döner."""
        cursor = await connection.execute(_START_QUERY, {"feed_id": feed_id, "trigger": trigger.value})
        row = await cursor.fetchone()
        assert row is not None  # INSERT ... RETURNING her zaman bir satır döner.
        run_id: UUID = row[0]
        return run_id

    async def finish(self, connection: psycopg.AsyncConnection[TupleRow], run_id: UUID, result: RunResult) -> None:
        """Okumanın sonucunu ve bitiş zamanını kaydeder."""
        await connection.execute(
            _FINISH_QUERY,
            {
                "run_id": run_id,
                "status": result.status.value,
                "http_status": result.http_status,
                "final_url": result.final_url,
                "items_received": result.items_received,
                "items_new": result.items_new,
                "items_duplicate": result.items_duplicate,
                "items_failed": result.items_failed,
                "error_message": result.error_message,
            },
        )
