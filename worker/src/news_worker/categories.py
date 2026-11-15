"""`categories` ve `category_mappings` tablolarının sorguları. Servisler SQL görmez; SQL yalnızca buradadır."""

import psycopg
from psycopg.rows import TupleRow

from news_worker.category_resolver import SourceCategoryMappings

_FIND_TOPIC_CODES_QUERY = """
    SELECT code
    FROM categories
    WHERE kind = 'TOPIC'
"""

_FIND_SOURCE_LANGUAGE_QUERY = """
    SELECT language
    FROM sources
    WHERE code = %(source_code)s
"""

_FIND_MAPPINGS_QUERY = """
    SELECT m.source_category, c.code
    FROM category_mappings m
    JOIN sources s ON s.id = m.source_id
    JOIN categories c ON c.id = m.category_id
    WHERE s.code = %(source_code)s
"""


class SourceNotFoundError(Exception):
    """Verilen koda sahip bir kaynak yok."""


class CategoryRepository:
    async def find_topic_codes(self, connection: psycopg.AsyncConnection[TupleRow]) -> frozenset[str]:
        """Konu kategorilerinin kodlarını döner; zaman etiketi olan Son Dakika bunların içinde değildir."""
        cursor = await connection.execute(_FIND_TOPIC_CODES_QUERY)
        return frozenset(code for (code,) in await cursor.fetchall())

    async def find_mappings(
        self, connection: psycopg.AsyncConnection[TupleRow], source_code: str
    ) -> SourceCategoryMappings:
        """Kaynağın dilini ve haber düzeyindeki eşlemelerini döner. Eşlemesi olmayan kaynak hata değildir."""
        parameters = {"source_code": source_code}
        cursor = await connection.execute(_FIND_SOURCE_LANGUAGE_QUERY, parameters)
        row = await cursor.fetchone()
        if row is None:
            raise SourceNotFoundError(f"Kaynak bulunamadı: {source_code}")
        (language,) = row

        cursor = await connection.execute(_FIND_MAPPINGS_QUERY, parameters)
        return SourceCategoryMappings(
            language=language,
            category_code_by_source_category=dict(await cursor.fetchall()),
        )
