"""Hacim testi deneme verisinin testleri (FOG-07)."""

import random
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from elasticsearch import AsyncElasticsearch

from news_worker.articles import ArticleRepository
from news_worker.database import Database
from news_worker.volume_data import (
    PUBLISHED_WITHIN_DAYS,
    URL_PREFIX,
    LanguageProfile,
    TextGenerator,
    TextSample,
    VolumeDataError,
    VolumeDataGenerator,
    VolumeDataRepository,
    build_profiles,
    load_samples,
)

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)
SOURCE_CODE = "DENEME_TEST"

SAMPLES = [
    TextSample(
        "tr", "Ekonomi büyüme rakamları açıklandı", "Büyüme rakamları beklentiyi aştı", "<p>Merkez bankası faiz</p>"
    ),
    TextSample("tr", "Ekonomi faiz kararı", "Faiz sabit kaldı", None),
    TextSample("en", "Climate summit opens", "Leaders meet", "<p>The summit opened today</p>"),
]


def profiles() -> dict[str, LanguageProfile]:
    return build_profiles(SAMPLES)


# --- Kelime dağılımı ve metin üretimi --------------------------------------------------------------


def test_profile_counts_words_and_measures_lengths() -> None:
    """Kelimeler sıklıklarıyla sayılır; HTML etiketleri kelime sayılmaz; uzunluklar ve oranlar ölçülür."""
    turkish = profiles()["tr"]

    # Türkçe örneklerde 17 kelime var; en sık geçen "Ekonomi" (iki başlıkta). Eşit sıklıktakiler ilk görülme
    # sırasıyla gelir. Kümülatif sıklıkların sonuncusu toplam kelime sayısıdır.
    assert turkish.words[0] == "Ekonomi"
    assert (turkish.cumulative_weights[0], turkish.cumulative_weights[-1]) == (2, 17)
    assert "p" not in turkish.words
    # Ortalamalar yuvarlanır: başlık (4 + 3) / 2, özet (4 + 3) / 2, tam metin 3 kelime.
    assert (turkish.title_words, turkish.summary_words, turkish.content_words) == (4, 4, 3)
    assert (turkish.summary_ratio, turkish.content_ratio) == (1.0, 0.5)


def test_generated_texts_use_only_the_profile_words() -> None:
    """Üretilen başlık, özet ve tam metin yalnızca örneklerdeki kelimelerden oluşur; tam metin paragraflıdır."""
    turkish = profiles()["tr"]
    generator = TextGenerator(turkish, random.Random(1))

    title = generator.title()
    contents = [generator.content() for _ in range(20)]
    content = next(text for text in contents if text is not None)

    vocabulary = {word.lower() for word in turkish.words}
    for text in (title, content.replace("<p>", " ").replace("</p>", " ")):
        assert {word.strip(".").lower() for word in text.split()} <= vocabulary
    assert content.startswith("<p>") and content.endswith("</p>")
    # Örneklerin yarısında tam metin var; üretilenlerde de hem dolu hem boş tam metin bulunur.
    assert None in contents


def test_missing_language_is_reported() -> None:
    """Örneklerde Türkçe veya İngilizce haber yoksa deneme verisi üretilmez."""
    with pytest.raises(VolumeDataError, match="en"):
        build_profiles([sample for sample in SAMPLES if sample.language == "tr"])


async def test_samples_are_read_from_elasticsearch(search_client: AsyncElasticsearch) -> None:
    """Gerçek haberlerin metinleri, belgenin dilindeki alanlardan okunur."""
    index = f"articles-volume-test-{uuid.uuid4().hex}"
    await search_client.index(
        index=index,
        document={"language": "tr", "title_tr": "Başlık", "summary_tr": "Özet", "content_tr": "<p>Metin</p>"},
        refresh=True,
    )
    try:
        samples = await load_samples(search_client, size=10, index=index)
    finally:
        await search_client.indices.delete(index=index)

    assert samples == [TextSample("tr", "Başlık", "Özet", "<p>Metin</p>")]


async def test_rare_language_is_sampled_too(search_client: AsyncElasticsearch) -> None:
    """Örnekler her dilden ayrı istenir: az olan İngilizce haberler de örneğe girer.

    Kümede 5.300 Türkçe habere karşı 18 İngilizce haber vardı; dil ayırmadan istenen 3.000 örneğe hiç
    girmemişlerdi (24 Kasım 2026).
    """
    index = f"articles-volume-test-{uuid.uuid4().hex}"
    for number in range(3):
        await search_client.index(index=index, document={"language": "tr", "title_tr": f"Türkçe {number}"})
    await search_client.index(index=index, document={"language": "en", "title_en": "English"}, refresh=True)
    try:
        samples = await load_samples(search_client, size=2, index=index)
    finally:
        await search_client.indices.delete(index=index)

    assert sorted(sample.language for sample in samples) == ["en", "tr", "tr"]


# --- Veritabanına yazma -----------------------------------------------------------------------------


@pytest.fixture
def volume_source(admin: psycopg.Connection) -> Iterator[uuid.UUID]:
    """Kapalı deneme kaynağı ve beslemesi; yönetim panelinin oluşturacağı satırların aynısı."""
    row = admin.execute(
        "INSERT INTO sources (code, name, homepage_url, reader_type, language, request_interval_seconds, enabled) "
        "VALUES (%s, 'Deneme verisi (test)', 'https://deneme.invalid/', 'RSS', 'tr', 60, false) RETURNING id",
        (SOURCE_CODE,),
    ).fetchone()
    assert row is not None
    source_id: uuid.UUID = row[0]
    admin.execute(
        "INSERT INTO feeds (source_id, name, url, use_item_categories, enabled, disabled_reason) "
        "VALUES (%s, 'deneme', 'https://deneme.invalid/rss-test', false, false, 'MANUAL')",
        (source_id,),
    )
    # Deneme haberlerinin kategorileri gerçek haberlerdeki dağılımdan seçilir: Ekonomi ve Spor kategorili
    # gerçek bir TRT haberi. Ortak temizlik test sonunda bütün haberleri siler.
    real = admin.execute(
        "INSERT INTO articles (source_id, external_id, url, normalized_url, title, language, item_type, "
        "                      published_at, fetched_at, lifecycle_state) "
        "SELECT id, 'gercek-1', 'https://trt.test/1', 'https://trt.test/1', 'Gerçek haber', 'tr', 'ARTICLE', "
        "       now(), now(), 'HOT' FROM sources WHERE code = 'TRT' RETURNING id"
    ).fetchone()
    assert real is not None
    admin.execute(
        "INSERT INTO article_categories (article_id, category_id, mapping_level) "
        "SELECT %s, id, 'ITEM' FROM categories WHERE code IN ('ECONOMY', 'SPORTS')",
        (real[0],),
    )
    yield source_id
    # Ortak temizlik kaynakları silmez; deneme kaynağı haberleriyle birlikte burada silinir.
    admin.execute(
        "DELETE FROM outbox_events WHERE article_id IN (SELECT id FROM articles WHERE source_id = %s)", (source_id,)
    )
    admin.execute("DELETE FROM articles WHERE source_id = %s", (source_id,))
    admin.execute("DELETE FROM feeds WHERE source_id = %s", (source_id,))
    admin.execute("DELETE FROM sources WHERE id = %s", (source_id,))


def build_generator(database: Database) -> VolumeDataGenerator:
    return VolumeDataGenerator(database, VolumeDataRepository(), ArticleRepository(), profiles(), batch_size=7, now=NOW)


async def test_articles_are_written_through_the_ingestion_path(
    database: Database, admin: psycopg.Connection, volume_source: uuid.UUID
) -> None:
    """Deneme haberleri gerçek haberler gibi kaydedilir: kategorisi ve metinli outbox notuyla."""
    result = await build_generator(database).run(30, SOURCE_CODE)

    assert (result.inserted, result.skipped) == (30, 0)
    rows = admin.execute(
        "SELECT a.url, a.language, a.published_at, array_agg(c.code), "
        "       (SELECT count(*) FROM outbox_events o WHERE o.article_id = a.id AND o.payload IS NOT NULL) "
        "FROM articles a JOIN article_categories ac ON ac.article_id = a.id JOIN categories c ON c.id = ac.category_id "
        "WHERE a.source_id = %s GROUP BY a.id",
        (volume_source,),
    ).fetchall()
    assert len(rows) == 30
    assert all(url.startswith(URL_PREFIX) for url, *_ in rows)
    assert {language for _, language, *_ in rows} <= {"tr", "en"}
    assert all(NOW - timedelta(days=PUBLISHED_WITHIN_DAYS) <= published <= NOW for _, _, published, *_ in rows)
    # Her haberin gerçek haberlerde geçen bir kategorisi ve Elasticsearch'e aktarılacak, metinli bir notu var.
    assert all(len(categories) == 1 and categories[0] in {"ECONOMY", "SPORTS"} for *_, categories, _ in rows)
    assert all(notes == 1 for *_, notes in rows)


async def test_rerun_skips_saved_articles_and_continues(
    database: Database, admin: psycopg.Connection, volume_source: uuid.UUID
) -> None:
    """Yarıda kalan çalışma yeniden başlatılırsa kayıtlı haberler atlanır, kalanlar eklenir."""
    await build_generator(database).run(20, SOURCE_CODE)

    again = await build_generator(database).run(20, SOURCE_CODE)
    more = await build_generator(database).run(25, SOURCE_CODE)

    assert (again.inserted, again.skipped) == (0, 20)
    assert (more.inserted, more.skipped) == (5, 20)
    row = admin.execute("SELECT count(*) FROM articles WHERE source_id = %s", (volume_source,)).fetchone()
    assert row == (25,)


async def test_enabled_source_is_refused(
    database: Database, admin: psycopg.Connection, volume_source: uuid.UUID
) -> None:
    """Açık kaynağa deneme verisi yazılmaz: işçi onu okur ve içeriği silinemez."""
    admin.execute("UPDATE sources SET enabled = true WHERE id = %s", (volume_source,))

    with pytest.raises(VolumeDataError, match="açık"):
        await build_generator(database).run(5, SOURCE_CODE)

    row = admin.execute("SELECT count(*) FROM articles WHERE source_id = %s", (volume_source,)).fetchone()
    assert row == (0,)


async def test_missing_source_or_feed_is_refused(
    database: Database, admin: psycopg.Connection, volume_source: uuid.UUID
) -> None:
    """Kaynak yoksa veya beslemesi yoksa ne yapılması gerektiği söylenir."""
    with pytest.raises(VolumeDataError, match="kaynağı yok"):
        await build_generator(database).run(5, "BOYLE_BIR_KAYNAK_YOK")

    admin.execute("DELETE FROM feeds WHERE source_id = %s", (volume_source,))
    with pytest.raises(VolumeDataError, match="beslemesi yok"):
        await build_generator(database).run(5, SOURCE_CODE)


async def test_without_real_categories_nothing_is_written(
    database: Database, admin: psycopg.Connection, volume_source: uuid.UUID
) -> None:
    """Gerçek haberlerde kategori yoksa kategorilerin dağılımı bilinemez; haber yazılmaz."""
    admin.execute("DELETE FROM article_categories")

    with pytest.raises(VolumeDataError, match="kategori"):
        await build_generator(database).run(5, SOURCE_CODE)

    row = admin.execute("SELECT count(*) FROM articles WHERE source_id = %s", (volume_source,)).fetchone()
    assert row == (0,)
