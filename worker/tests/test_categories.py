from pathlib import Path

import psycopg
import pytest

from news_worker.categories import CategoryRepository, SourceNotFoundError
from news_worker.category_resolver import (
    AssignedCategory,
    CategoryResolver,
    FeedCategoryRule,
    MappingLevel,
    SourceCategoryMappings,
)
from news_worker.database import Database
from news_worker.feed_reader import FeedReader
from news_worker.text_normalizer import normalize_category

FIXTURES = Path(__file__).parent / "fixtures" / "feeds"


async def find_topic_codes(database: Database) -> frozenset[str]:
    async with await database.connect() as connection:
        return await CategoryRepository().find_topic_codes(connection)


async def find_mappings(database: Database, source_code: str) -> SourceCategoryMappings:
    async with await database.connect() as connection:
        return await CategoryRepository().find_mappings(connection, source_code)


async def test_topic_codes_do_not_include_breaking(database: Database) -> None:
    """Konu kategorileri okunur; zaman etiketi olan Son Dakika aralarında değildir."""
    topic_codes = await find_topic_codes(database)

    assert "BREAKING" not in topic_codes
    assert {"GENERAL", "WORLD", "OTHER"} <= topic_codes
    assert len(topic_codes) == 9


async def test_mappings_are_read_with_source_language(database: Database) -> None:
    """Kaynağın dili ve eşlemeleri birlikte gelir; işçi kendi kullanıcısıyla (news_worker) okuyabilir."""
    ntv = await find_mappings(database, "NTV")
    global_voices = await find_mappings(database, "GLOBALVOICES")

    assert ntv.language == "tr"
    assert ntv.category_code_by_source_category["spor&skor"] == "SPORTS"
    assert global_voices.language == "en"
    assert global_voices.category_code_by_source_category["arts & culture"] == "CULTURE_ARTS"


async def test_unknown_source_raises_error(database: Database) -> None:
    """Var olmayan bir kaynak kodu sessizce boş eşleme dönmez, hata verir."""
    with pytest.raises(SourceNotFoundError):
        await find_mappings(database, "YOK")


def test_seeded_source_categories_are_stored_normalized(admin: psycopg.Connection) -> None:
    """Betikteki her değer, işçinin karşılaştırırken üreteceği biçimde (küçük harf, boşluksuz) saklanır."""
    rows = admin.execute(
        "SELECT m.source_category, s.language FROM category_mappings m JOIN sources s ON s.id = m.source_id"
    ).fetchall()

    assert rows
    assert all(normalize_category(source_category, language) == source_category for source_category, language in rows)


@pytest.mark.parametrize(
    ("source_code", "fixture_name", "feed_rule", "expected"),
    [
        (
            "TRT",
            "trt-gundem.xml",
            FeedCategoryRule(default_category_code="BREAKING", use_item_categories=True),
            (AssignedCategory("BREAKING", MappingLevel.FEED), AssignedCategory("GENERAL", MappingLevel.ITEM)),
        ),
        (
            "TRT",
            "trt-koronavirus.xml",
            FeedCategoryRule(default_category_code=None, use_item_categories=True),
            (AssignedCategory("HEALTH", MappingLevel.ITEM),),
        ),
        (
            "NTV",
            "ntv-turkiye.xml",
            FeedCategoryRule(default_category_code="BREAKING", use_item_categories=True),
            (AssignedCategory("BREAKING", MappingLevel.FEED), AssignedCategory("GENERAL", MappingLevel.ITEM)),
        ),
        (
            "CNNTURK",
            "cnnturk-all.xml",
            FeedCategoryRule(default_category_code=None, use_item_categories=True),
            (AssignedCategory("WORLD", MappingLevel.ITEM),),
        ),
        (
            "GLOBALVOICES",
            "globalvoices.xml",
            FeedCategoryRule(default_category_code="WORLD", use_item_categories=True),
            (AssignedCategory("WORLD", MappingLevel.FEED),),
        ),
    ],
    ids=["trt-breaking", "trt-mixed", "ntv-breaking", "cnnturk-video-url", "globalvoices-default"],
)
async def test_real_articles_are_resolved_with_seeded_mappings(
    database: Database,
    source_code: str,
    fixture_name: str,
    feed_rule: FeedCategoryRule,
    expected: tuple[AssignedCategory, ...],
) -> None:
    """Uçtan uca: gerçek beslemedeki ilk haber, veritabanındaki eşlemelerle (V13) beklenen kategorileri alır."""
    article = FeedReader().read((FIXTURES / fixture_name).read_bytes()).articles[0]
    resolver = CategoryResolver(await find_topic_codes(database))

    assigned = resolver.resolve(article.source_categories, feed_rule, await find_mappings(database, source_code))

    assert assigned == expected


async def test_real_article_with_matching_topic_gets_extra_category(database: Database) -> None:
    """Global Voices'ın `Education` ve `Health` etiketli haberi Dünya'ya ek olarak bu konuları da alır."""
    article = FeedReader().read((FIXTURES / "globalvoices.xml").read_bytes()).articles[1]
    assert {"Education", "Health"} <= set(article.source_categories)
    resolver = CategoryResolver(await find_topic_codes(database))
    feed_rule = FeedCategoryRule(default_category_code="WORLD", use_item_categories=True)

    assigned = resolver.resolve(article.source_categories, feed_rule, await find_mappings(database, "GLOBALVOICES"))

    assert assigned == (
        AssignedCategory("WORLD", MappingLevel.FEED),
        AssignedCategory("LIFESTYLE", MappingLevel.ITEM),
        AssignedCategory("HEALTH", MappingLevel.ITEM),
    )
