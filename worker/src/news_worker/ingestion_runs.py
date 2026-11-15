"""`ingestion_runs` tablosunun sorguları: her besleme okumasının kaydı (FG-VT-10)."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

import psycopg
from psycopg.rows import TupleRow


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


# Elle başlatılan toplamayı zamanlanmış olandan ayırt etmek yönetim ekranıyla birlikte
# gelecek (İ-22); o zamana kadar bütün okumalar SCHEDULED olarak kaydedilir.
_START_QUERY = """
    INSERT INTO ingestion_runs (feed_id, trigger, status, started_at)
    VALUES (%(feed_id)s, 'SCHEDULED', 'RUNNING', now())
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


class IngestionRunRepository:
    async def start(self, connection: psycopg.AsyncConnection[TupleRow], feed_id: UUID) -> UUID:
        """Okumanın başladığını kaydeder ve kaydın kimliğini döner."""
        cursor = await connection.execute(_START_QUERY, {"feed_id": feed_id})
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
