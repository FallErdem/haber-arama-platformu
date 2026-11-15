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

from news_worker.category_resolver import AssignedCategory
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
        """Haberi kategorileri, görselleri ve outbox notuyla kaydeder.

        Haber daha önce kaydedilmişse hiçbir şey yazmaz ve False döner; yeni kaydedildiyse True döner.
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
