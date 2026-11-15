from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import psycopg
import pytest

from news_worker.articles import ArticleRepository, NewArticle, UnknownCategoryError
from news_worker.category_resolver import AssignedCategory, MappingLevel
from news_worker.database import Database
from news_worker.parsed_article import ItemType, ParsedArticle

FETCHED_AT = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)

ARTICLE = ParsedArticle(
    external_id="haber-1",
    url="https://example.test/ekonomi/haber-1/",
    normalized_url="https://example.test/ekonomi/haber-1",
    title="Örnek haber",
    summary="Kısa özet.",
    content="<p>Tam metin.</p>",
    author="Örnek Yazar",
    published_at=FETCHED_AT - timedelta(hours=2),
    item_type=ItemType.ARTICLE,
    image_urls=("https://example.test/ana.jpg", "https://example.test/ikinci.jpg"),
    source_categories=("ekonomi",),
)

CATEGORIES = (
    AssignedCategory("BREAKING", MappingLevel.FEED),
    AssignedCategory("ECONOMY", MappingLevel.ITEM),
)


@pytest.fixture
def trt_feed(admin: psycopg.Connection) -> tuple[UUID, UUID]:
    """TRT kaynağının ve bir beslemesinin kimlikleri. `admin` kullanıldığı için test sonunda haberler silinir."""
    row = admin.execute(
        "SELECT s.id, f.id FROM feeds f JOIN sources s ON s.id = f.source_id "
        "WHERE s.code = 'TRT' ORDER BY f.name LIMIT 1"
    ).fetchone()
    assert row is not None
    return row[0], row[1]


def new_article(feed: tuple[UUID, UUID], article: ParsedArticle = ARTICLE) -> NewArticle:
    source_id, feed_id = feed
    return NewArticle(
        source_id=source_id,
        feed_id=feed_id,
        language="tr",
        article=article,
        categories=CATEGORIES,
        fetched_at=FETCHED_AT,
    )


async def insert(database: Database, article: NewArticle) -> bool:
    """Haberi işçinin kendi kullanıcısıyla (news_worker) kaydeder."""
    async with await database.connect() as connection:
        return await ArticleRepository().insert_if_new(connection, article)


def count(admin: psycopg.Connection, table: str) -> int:
    row = admin.execute(f"SELECT count(*) FROM {table}").fetchone()
    assert row is not None
    result: int = row[0]
    return result


async def test_new_article_is_stored_with_its_fields(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID]
) -> None:
    """Yeni haber bütün alanlarıyla kaydedilir."""
    inserted = await insert(database, new_article(trt_feed))

    assert inserted is True
    row = admin.execute(
        "SELECT source_id, feed_id, external_id, url, normalized_url, title, summary, content, author, "
        "language, item_type, published_at, fetched_at, lifecycle_state, hidden FROM articles"
    ).fetchone()
    assert row == (
        trt_feed[0],
        trt_feed[1],
        "haber-1",
        "https://example.test/ekonomi/haber-1/",
        "https://example.test/ekonomi/haber-1",
        "Örnek haber",
        "Kısa özet.",
        "<p>Tam metin.</p>",
        "Örnek Yazar",
        "tr",
        "ARTICLE",
        ARTICLE.published_at,
        FETCHED_AT,
        "HOT",
        False,
    )


async def test_categories_images_and_outbox_are_stored_with_the_article(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID]
) -> None:
    """Haberle birlikte kategorileri, görsel kuyruğu kayıtları ve outbox notu da yazılır."""
    await insert(database, new_article(trt_feed))

    categories = admin.execute(
        "SELECT c.code, ac.mapping_level FROM article_categories ac "
        "JOIN categories c ON c.id = ac.category_id ORDER BY c.code"
    ).fetchall()
    media = admin.execute(
        "SELECT media_type, position, source_url, status, storage_key FROM media ORDER BY position"
    ).fetchall()
    outbox = admin.execute(
        "SELECT o.operation, o.status, o.article_id = a.id FROM outbox_events o CROSS JOIN articles a"
    ).fetchall()

    assert categories == [("BREAKING", "FEED"), ("ECONOMY", "ITEM")]
    assert media == [
        ("IMAGE", 0, "https://example.test/ana.jpg", "PENDING", None),
        ("IMAGE", 1, "https://example.test/ikinci.jpg", "PENDING", None),
    ]
    assert outbox == [("INDEX", "PENDING", True)]


async def test_article_with_same_external_id_is_ignored_and_first_one_is_kept(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID]
) -> None:
    """Aynı kaynaktan aynı kimlikli haber ikinci kez kaydedilmez; ilk kayıt değişmez (FG-VT-04)."""
    await insert(database, new_article(trt_feed))
    changed = replace(
        ARTICLE, title="Değişmiş başlık", url="https://example.test/x", normalized_url="https://example.test/x"
    )

    inserted = await insert(database, new_article(trt_feed, changed))

    assert inserted is False
    assert admin.execute("SELECT title FROM articles").fetchall() == [("Örnek haber",)]
    # Atlanan haber için kategori, görsel veya outbox kaydı da oluşmaz.
    assert count(admin, "article_categories") == 2
    assert count(admin, "media") == 2
    assert count(admin, "outbox_events") == 1


async def test_article_with_same_normalized_url_is_ignored(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID]
) -> None:
    """Kimliği farklı olsa da normalleştirilmiş adresi aynı olan haber kaydedilmez."""
    await insert(database, new_article(trt_feed))
    same_url = replace(ARTICLE, external_id="baska-kimlik", url="https://example.test/ekonomi/haber-1?utm_source=rss")

    inserted = await insert(database, new_article(trt_feed, same_url))

    assert inserted is False
    assert count(admin, "articles") == 1


async def test_same_external_id_from_another_source_is_a_different_article(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID]
) -> None:
    """Tekrar kontrolü kaynak bazındadır: başka bir kaynağın aynı kimlikli haberi ayrıca kaydedilir."""
    row = admin.execute(
        "SELECT s.id, f.id FROM feeds f JOIN sources s ON s.id = f.source_id "
        "WHERE s.code = 'NTV' ORDER BY f.name LIMIT 1"
    ).fetchone()
    assert row is not None
    await insert(database, new_article(trt_feed))

    inserted = await insert(database, new_article((row[0], row[1])))

    assert inserted is True
    assert count(admin, "articles") == 2


@pytest.mark.parametrize(
    ("age", "expected_state"),
    [
        (timedelta(days=29), "HOT"),
        (timedelta(days=31), "WARM"),
        (timedelta(days=360), "WARM"),
        (timedelta(days=400), "COLD"),
    ],
    ids=["29-days", "31-days", "360-days", "400-days"],
)
async def test_lifecycle_state_follows_publication_date(
    database: Database,
    admin: psycopg.Connection,
    trt_feed: tuple[UUID, UUID],
    age: timedelta,
    expected_state: str,
) -> None:
    """Eski tarihli haber toplandığında yaşam döngüsü durumu yayın tarihine göre belirlenir (ADR-0011)."""
    old_article = replace(ARTICLE, published_at=FETCHED_AT - age)

    await insert(database, new_article(trt_feed, old_article))

    assert admin.execute("SELECT lifecycle_state FROM articles").fetchall() == [(expected_state,)]


async def test_article_without_optional_fields_is_stored(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID]
) -> None:
    """Özeti, içeriği, yazarı ve görseli olmayan haber de kaydedilir (CNN Türk içerik ve yazar vermez)."""
    bare = replace(ARTICLE, summary=None, content=None, author=None, image_urls=())

    inserted = await insert(database, new_article(trt_feed, bare))

    assert inserted is True
    assert admin.execute("SELECT summary, content, author FROM articles").fetchall() == [(None, None, None)]
    assert count(admin, "media") == 0
    assert count(admin, "outbox_events") == 1


async def test_nothing_is_stored_when_a_step_fails(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID]
) -> None:
    """Tek işlem: kategori yazılırken hata olursa haberin kendisi de geri alınır."""
    broken = replace(new_article(trt_feed), categories=(AssignedCategory("YOK", MappingLevel.ITEM),))

    with pytest.raises(UnknownCategoryError):
        await insert(database, broken)

    assert count(admin, "articles") == 0
    assert count(admin, "article_categories") == 0
    assert count(admin, "outbox_events") == 0
