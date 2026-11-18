"""Haberlerin kaydedilmesi. Servisler SQL görmez; SQL yalnızca buradadır.

Bir haber dört tabloya birlikte yazılır: haberin meta verisi (`articles`), kategorileri
(`article_categories`), indirilecek görselleri (`media`) ve Elasticsearch'e aktarım notu
(`outbox_events`, ADR-0012). Hepsi tek işlemdedir: ya hepsi yazılır ya hiçbiri.

Haberin metinleri (özet, tam metin, yazar) PostgreSQL'e yazılmaz; tek kayıtları Elasticsearch'tir
(ADR-0019). Metinler outbox notunda taşınır ve not aktarılınca nottan da silinir.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import psycopg
from psycopg.rows import TupleRow
from psycopg.types.json import Jsonb

from news_worker.category_resolver import OTHER_CATEGORY_CODE, AssignedCategory
from news_worker.parsed_article import ParsedArticle
from news_worker.search_document import ArticleMetadata, ArticleTexts


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
        source_id, feed_id, external_id, url, normalized_url, title,
        language, item_type, published_at, fetched_at, lifecycle_state
    )
    VALUES (
        %(source_id)s, %(feed_id)s, %(external_id)s, %(url)s, %(normalized_url)s, %(title)s,
        %(language)s, %(item_type)s, %(published_at)s, %(fetched_at)s,
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
# payload: haberin metinleri; yalnızca haber ilk kaydedilirken doludur (ADR-0019). Meta veri
# değişikliklerinin notlarında boştur.
_INSERT_OUTBOX_QUERY = """
    INSERT INTO outbox_events (article_id, operation, status, next_attempt_at, payload)
    VALUES (%(article_id)s, 'INDEX', 'PENDING', now(), %(payload)s)
"""

# Arama indeksine yazılacak meta veri: kaynak kodu ve kategori kodlarıyla birlikte, tek sorguda.
# Gizlenen haberler de gelir: belgeleri indekste kalır, `hidden` alanıyla aramadan çıkarılır. array_agg
# kategori kodlarını tek bir dizide toplar; FILTER, kategorisi olmayan haberde dizinin [NULL] yerine
# boş olmasını sağlar.
_METADATA_SELECT = """
    SELECT a.id, s.code, a.language, a.item_type, a.published_at, a.group_id, a.title, a.hidden,
           COALESCE(array_agg(c.code ORDER BY c.code) FILTER (WHERE c.code IS NOT NULL), '{}'::text[])
    FROM articles a
    JOIN sources s ON s.id = a.source_id
    LEFT JOIN article_categories ac ON ac.article_id = a.id
    LEFT JOIN categories c ON c.id = ac.category_id
"""

_FIND_METADATA_QUERY = (
    _METADATA_SELECT
    + """
    WHERE a.id = ANY(%(article_ids)s::uuid[])
    GROUP BY a.id, s.code
"""
)

# Tam yeniden indeksleme için bütün haberler, kimlik sırasıyla ve sayfa sayfa. Sayfalama
# "şu kimlikten sonrakiler" diye yapılır (OFFSET değil): her sayfa birincil anahtar indeksiyle
# doğrudan bulunur, baştan sayılmaz.
_FIND_METADATA_AFTER_QUERY = (
    _METADATA_SELECT
    + """
    WHERE (%(after_id)s::uuid IS NULL OR a.id > %(after_id)s::uuid)
    GROUP BY a.id, s.code
    ORDER BY a.id
    LIMIT %(limit)s
"""
)


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

            # Metinler haberle aynı işlemde nota yazılır: haber kaydedildiyse metni de kaybolmaz.
            texts = ArticleTexts(summary=article.summary, content=article.content, author=article.author)
            await connection.execute(
                _INSERT_OUTBOX_QUERY, {"article_id": article_id, "payload": Jsonb(texts.to_payload())}
            )
            return True

    async def find_metadata(
        self, connection: psycopg.AsyncConnection[TupleRow], article_ids: Sequence[UUID]
    ) -> dict[UUID, ArticleMetadata]:
        """Verilen kimliklerdeki haberlerin meta verisi, haber kimliğine göre.

        Silinmiş bir haber sözlükte yer almaz; çağıran, istediği kimlik sözlükte yoksa haberin
        indekste bulunmaması gerektiğini anlar. Gizlenmiş haber `hidden=True` ile gelir.
        """
        cursor = await connection.execute(_FIND_METADATA_QUERY, {"article_ids": list(article_ids)})
        return {row[0]: _to_metadata(row) for row in await cursor.fetchall()}

    async def find_metadata_after(
        self, connection: psycopg.AsyncConnection[TupleRow], after_id: UUID | None, limit: int
    ) -> list[ArticleMetadata]:
        """Haberlerin bir sayfasını kimlik sırasıyla döner; `after_id` önceki sayfanın son kimliğidir.

        İlk sayfa için `after_id` verilmez. Boş liste, haberlerin bittiğini gösterir.
        """
        cursor = await connection.execute(_FIND_METADATA_AFTER_QUERY, {"after_id": after_id, "limit": limit})
        return [_to_metadata(row) for row in await cursor.fetchall()]

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
            # Kategoriler değişti: arama indeksindeki belgenin güncellenmesi için yeni bir not bırakılır.
            # Not metin taşımaz; belgede yalnızca meta veri alanları güncellenir.
            await connection.execute(_INSERT_OUTBOX_QUERY, {"article_id": article_id, "payload": None})


def _to_metadata(row: TupleRow) -> ArticleMetadata:
    return ArticleMetadata(
        id=row[0],
        source_code=row[1],
        language=row[2],
        item_type=row[3],
        published_at=row[4],
        group_id=row[5],
        title=row[6],
        hidden=row[7],
        categories=tuple(row[8]),
    )
