"""`sources` tablosunun işçinin açılışta baktığı sorgusu."""

from uuid import UUID

import psycopg
from psycopg.rows import TupleRow

_FIND_ENABLED_IDS_QUERY = """
    SELECT id
    FROM sources
    WHERE reader_type = %(reader_type)s
      AND enabled
    ORDER BY code
"""


class SourceRepository:
    async def find_enabled_ids(self, connection: psycopg.AsyncConnection[TupleRow], reader_type: str) -> list[UUID]:
        """Okuyucu türü verilen etkin kaynakların kimlikleri (örneğin NYT kaynağı)."""
        cursor = await connection.execute(_FIND_ENABLED_IDS_QUERY, {"reader_type": reader_type})
        return [row[0] for row in await cursor.fetchall()]
