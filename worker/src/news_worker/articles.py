"""Haberlerin kaydedilmesi. Servisler SQL görmez; SQL yalnızca buradadır.

Bir haber dört tabloya birlikte yazılır: haberin kendisi (`articles`), kategorileri
(`article_categories`), indirilecek görselleri (`media`) ve Elasticsearch'e aktarım notu
(`outbox_events`, ADR-0012). Hepsi tek işlemdedir: ya hepsi yazılır ya hiçbiri.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import psycopg
from psycopg.rows import TupleRow

from news_worker.category_resolver import OTHER_CATEGORY_CODE, AssignedCategory
from news_worker.parsed_article import ParsedArticle


@dataclass(frozen=True)
class NewArticle:
    """Kaydedilmeye hazır haber: okuyucunun çıktısı, kaynağı ve bulunan kategorileri."""

    source_id: UUID
    # Haberi getiren besleme.
    feed_id: UUID
    # Kaynağın dili (`sources.language`).
    language: str
    article: ParsedArticle
    categories: tuple[AssignedCategory, ...]
    fetched_at: datetime


class UnknownCategoryError(Exception):
    """Atanmak istenen kategori kodu `categories` tablosunda yok."""


# ON CONFLICT DO NOTHING: aynı kaynaktan aynı kimlikli veya aynı normalleştirilmiş adresli haber
# zaten varsa (iki benzersizlik kısıtından biri) satır eklenmez ve hata oluşmaz; ilk kaydedilen
# haber olduğu gibi kalır (FG-VT-04). RETURNING yalnızca gerçekten eklenen satır için değer döner.
#
# lifecycle_state: eski tarihli bir haber de toplanabilir (TRT'nin `koronavirus` beslemesi 2023
# haberleri verir); durum yayın tarihine göre belirlenir (ADR-0011: 30 güne kadar HOT,
# 1 yıla kadar WARM, daha eskisi COLD).
_INSERT_ARTICLE_QUERY = """
    INSERT INTO articles (
        source_id, feed_id, external_id, url, normalized_url, title, summary, content, author,
        language, item_type, published_at, fetched_at, lifecycle_state
    )
    VALUES (
        %(source_id)s, %(feed_id)s, %(external_id)s, %(url)s, %(normalized_url)s, %(title)s,
        %(summary)s, %(content)s, %(author)s, %(language)s, %(item_type)s, %(published_at)s,
        %(fetched_at)s,
        CASE
            WHEN %(published_at)s::timestamptz > %(fetched_at)s::timestamptz - interval '30 days' THEN 'HOT'
            WHEN %(published_at)s::timestamptz > %(fetched_at)s::timestamptz - interval '1 year' THEN 'WARM'
            ELSE 'COLD'
        END
    )
    ON CONFLICT DO NOTHING
    RETURNING id
"""

_INSERT_CATEGORY_QUERY = """
    INSERT INTO article_categories (article_id, category_id, mapping_level)
    SELECT %(article_id)s, id, %(mapping_level)s
    FROM categories
    WHERE code = %(category_code)s
"""

# Tekrar gelen haberin kayıtlı satırı. Tekrar, kimlikten veya normalleştirilmiş adresten
# anlaşılmış olabilir; ikisi farklı satırları gösterirse en eski kayıt (en küçük uuidv7) alınır.
_FIND_EXISTING_QUERY = """
    SELECT id
    FROM articles
    WHERE source_id = %(source_id)s
      AND (external_id = %(external_id)s OR normalized_url = %(normalized_url)s)
    ORDER BY id
    LIMIT 1
"""

# Kayıtlı habere eksik kategorisini ekler. Kategori zaten atanmışsa (birincil anahtar: haber +
# kategori) satır eklenmez ve ilk atandığı düzey korunur. Eklenen satır sayısı, kategorinin yeni
# olup olmadığını söyler; kategori kodu tabloda yoksa da hiçbir satır eklenmez.
_ADD_MISSING_CATEGORY_QUERY = """
    INSERT INTO article_categories (article_id, category_id, mapping_level)
    SELECT %(article_id)s, id, %(mapping_level)s
    FROM categories
    WHERE code = %(category_code)s
    ON CONFLICT DO NOTHING
"""

# Görsel indirme kuyruğu: PENDING ve deneme zamanı gelmiş kayıtları görsel indirme işi alır (İ-14).
_INSERT_MEDIA_QUERY = """
    INSERT INTO media (article_id, media_type, position, source_url, status, next_attempt_at)
    VALUES (%(article_id)s, 'IMAGE', %(position)s, %(source_url)s, 'PENDING', now())
"""

# Outbox notu: "bu haber Elasticsearch'e aktarılacak". Aktarım işi bekleyen notları işler (İ-15).
_INSERT_OUTBOX_QUERY = """
    INSERT INTO outbox_events (article_id, operation, status, next_attempt_at)
    VALUES (%(article_id)s, 'INDEX', 'PENDING', now())
"""


class ArticleRepository:
    async def insert_if_new(self, connection: psycopg.AsyncConnection[TupleRow], new_article: NewArticle) -> bool:
        """Haberi kategorileri, görselleri ve outbox notuyla kaydeder; yeni kaydedildiyse True döner.

        Haber daha önce kaydedilmişse haberin kendisi değişmez ve False döner. Yalnızca bu okumada
        bulunan kategorilerden eksik olanlar eklenir: bir haber birden fazla beslemede yer alabilir
        (önce `gundem`, sonra `sondakika`) ve her beslemenin kategorisini taşımalıdır.
        """
        article = new_article.article
        # transaction(): blok hatasız biterse dört tablodaki yazmalar birlikte kalıcı olur;
        # içeride bir hata olursa hepsi geri alınır.
        async with connection.transaction():
            cursor = await connection.execute(
                _INSERT_ARTICLE_QUERY,
                {
                    "source_id": new_article.source_id,
                    "feed_id": new_article.feed_id,
                    "external_id": article.external_id,
                    "url": article.url,
                    "normalized_url": article.normalized_url,
                    "title": article.title,
                    "summary": article.summary,
                    "content": article.content,
                    "author": article.author,
                    "language": new_article.language,
                    "item_type": article.item_type.value,
                    "published_at": article.published_at,
                    "fetched_at": new_article.fetched_at,
                },
            )
            row = await cursor.fetchone()
            if row is None:
                await self._add_missing_categories(connection, new_article)
                return False
            (article_id,) = row

            for category in new_article.categories:
                cursor = await connection.execute(
                    _INSERT_CATEGORY_QUERY,
                    {
                        "article_id": article_id,
                        "category_code": category.category_code,
                        "mapping_level": category.level.value,
                    },
                )
                if cursor.rowcount != 1:
                    raise UnknownCategoryError(f"Kategori bulunamadı: {category.category_code}")

            # Sıra numarası 0 olan görsel haberin ana görselidir.
            for position, image_url in enumerate(article.image_urls):
                await connection.execute(
                    _INSERT_MEDIA_QUERY,
                    {"article_id": article_id, "position": position, "source_url": image_url},
                )

            await connection.execute(_INSERT_OUTBOX_QUERY, {"article_id": article_id})
            return True

    async def _add_missing_categories(
        self, connection: psycopg.AsyncConnection[TupleRow], new_article: NewArticle
    ) -> None:
        """Tekrar gelen haberin kayıtlı satırına, bu okumada bulunan eksik kategorileri ekler."""
        article = new_article.article
        cursor = await connection.execute(
            _FIND_EXISTING_QUERY,
            {
                "source_id": new_article.source_id,
                "external_id": article.external_id,
                "normalized_url": article.normalized_url,
            },
        )
        row = await cursor.fetchone()
        if row is None:
            return
        (article_id,) = row

        added = 0
        for category in new_article.categories:
            # Diğer, "hiçbir konu bulunamadı" demektir ve yalnızca haber ilk kaydedilirken atanır;
            # konusu bulunmuş bir habere, konuyu bulamayan başka bir besleme yüzünden eklenmez.
            if category.category_code == OTHER_CATEGORY_CODE:
                continue
            cursor = await connection.execute(
                _ADD_MISSING_CATEGORY_QUERY,
                {
                    "article_id": article_id,
                    "category_code": category.category_code,
                    "mapping_level": category.level.value,
                },
            )
            added += cursor.rowcount

        if added:
            # Kategoriler değişti: arama indeksindeki kopyanın güncellenmesi için yeni bir not bırakılır.
            await connection.execute(_INSERT_OUTBOX_QUERY, {"article_id": article_id})
