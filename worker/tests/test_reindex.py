"""Tam yeniden indekslemenin testleri: gerçek PostgreSQL ve gerçek Elasticsearch, işçinin yetkileriyle.

Metinlerin tek kaydı Elasticsearch olduğundan (ADR-0019) belgeler eski nesilden kopyalanır; meta veri
PostgreSQL'den yazılır.
"""

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

import psycopg
import pytest
from elasticsearch import AsyncElasticsearch

from news_worker import reindex
from news_worker.articles import ArticleRepository, NewArticle
from news_worker.category_resolver import AssignedCategory, MappingLevel
from news_worker.config import Settings
from news_worker.database import Database
from news_worker.outbox import OutboxRepository
from news_worker.outbox_relay import OutboxRelay
from news_worker.parsed_article import ItemType, ParsedArticle
from news_worker.reindex import Reindexer, ReindexError
from news_worker.search_index import ALIAS, DocumentWrite, SearchIndex, index_name_for

NOVEMBER = datetime(2026, 11, 13, 13, 40, tzinfo=UTC)
JUNE_2023 = datetime(2023, 6, 6, 16, 2, tzinfo=UTC)


async def add_article(
    database: Database, feed: tuple[UUID, UUID], number: int, published_at: datetime = NOVEMBER
) -> None:
    article = ParsedArticle(
        external_id=f"haber-{number}",
        url=f"https://example.test/haber-{number}",
        normalized_url=f"https://example.test/haber-{number}",
        title=f"Örnek haber {number}",
        summary=f"Özet {number}",
        content=f"<p>Tam metin {number}</p>",
        author="Örnek Yazar",
        published_at=published_at,
        item_type=ItemType.ARTICLE,
        image_urls=(),
        source_categories=(),
    )
    new_article = NewArticle(
        source_id=feed[0],
        feed_id=feed[1],
        language="tr",
        article=article,
        categories=(AssignedCategory("GENERAL", MappingLevel.FEED),),
        fetched_at=NOVEMBER,
    )
    async with await database.connect() as connection:
        assert await ArticleRepository().insert_if_new(connection, new_article)


def build_relay(database: Database, client: AsyncElasticsearch) -> OutboxRelay:
    return OutboxRelay(
        database,
        OutboxRepository(),
        ArticleRepository(),
        client,
        SearchIndex(client),
        interval_seconds=60,
        batch_size=50,
    )


def build_reindexer(database: Database, client: AsyncElasticsearch, page_size: int = 500) -> Reindexer:
    return Reindexer(database, ArticleRepository(), SearchIndex(client), page_size)


async def searchable_titles(client: AsyncElasticsearch) -> list[str]:
    """Takma ad üzerinden, aramanın gördüğü gibi (gizli olanlar hariç) bulunan haberlerin başlıkları."""
    await client.indices.refresh(index=ALIAS, ignore_unavailable=True)
    response = await client.search(
        index=ALIAS,
        query={"bool": {"must_not": {"term": {"hidden": True}}}},
        size=100,
        ignore_unavailable=True,
        allow_no_indices=True,
    )
    return sorted(hit["_source"]["title_tr"] for hit in response["hits"]["hits"])


async def source_of(client: AsyncElasticsearch, admin: psycopg.Connection, number: int) -> dict[str, object]:
    """Haberin etkin nesildeki belgesi (yayın tarihi Kasım 2026)."""
    row = admin.execute("SELECT id FROM articles WHERE external_id = %s", (f"haber-{number}",)).fetchone()
    assert row is not None
    generation = await SearchIndex(client).active_generation()
    document = await client.get(index=index_name_for(NOVEMBER, generation), id=str(row[0]))
    source: dict[str, object] = document["_source"]
    return source


async def index_names(client: AsyncElasticsearch) -> list[str]:
    return sorted((await client.indices.get(index="articles-*", expand_wildcards="all")).body)


async def test_reindex_rewrites_all_articles_into_a_new_generation(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], search_client: AsyncElasticsearch
) -> None:
    """Bütün haberler yeni nesle yazılır, takma ad taşınır, eski nesil silinir; arama her haberi bir kez görür."""
    await add_article(database, trt_feed, 1)
    await add_article(database, trt_feed, 2, published_at=JUNE_2023)
    relay = build_relay(database, search_client)
    await SearchIndex(search_client).ensure_ready()
    await relay.relay_batch()
    assert await index_names(search_client) == ["articles-g1-2023.06.01", "articles-g1-2026.11.01"]

    new_generation = await build_reindexer(database, search_client).run()

    assert new_generation == 2
    assert await index_names(search_client) == ["articles-g2-2023.06.01", "articles-g2-2026.11.01"]
    assert await searchable_titles(search_client) == ["Örnek haber 1", "Örnek haber 2"]
    assert await SearchIndex(search_client).active_generation() == 2


async def test_reindex_keeps_the_texts_of_the_old_generation(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], search_client: AsyncElasticsearch
) -> None:
    """Metinler PostgreSQL'de olmadığı için eski nesildeki belgelerden kopyalanır; yeni nesilde aynen durur."""
    await add_article(database, trt_feed, 1)
    await SearchIndex(search_client).ensure_ready()
    await build_relay(database, search_client).relay_batch()

    await build_reindexer(database, search_client).run()

    source = await source_of(search_client, admin, 1)
    assert source["summary_tr"] == "Özet 1"
    assert source["content_tr"] == "<p>Tam metin 1</p>"
    assert source["author"] == "Örnek Yazar"


async def test_reindex_applies_the_current_template_to_old_documents(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], search_client: AsyncElasticsearch
) -> None:
    """Asıl kullanım: şablon değiştikten sonra eski belgeler yeni alanları (katlanmış alt alan) kazanır."""
    # İlk sürümdeki gibi: tek şablon, katlanmış alt alan yok.
    await search_client.indices.put_index_template(
        name="articles",
        index_patterns=["articles-*"],
        template={
            "mappings": {"properties": {"title_tr": {"type": "text", "analyzer": "turkish"}}},
            "aliases": {ALIAS: {}},
        },
    )
    await add_article(database, trt_feed, 1)
    await build_relay(database, search_client).relay_batch()
    folded_query = {"match": {"title_tr.folded": "ORNEK"}}
    await search_client.indices.refresh(index=ALIAS)
    assert (await search_client.count(index=ALIAS, query=folded_query))["count"] == 0

    await build_reindexer(database, search_client).run()

    await search_client.indices.refresh(index=ALIAS)
    assert (await search_client.count(index=ALIAS, query=folded_query))["count"] == 1
    # Eski tek şablon da silinmiştir.
    templates = await search_client.indices.get_index_template(name="articles*")
    assert [template["name"] for template in templates["index_templates"]] == ["articles-g2"]


async def test_reindex_repairs_differences_between_the_two_stores(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], search_client: AsyncElasticsearch
) -> None:
    """Tutarsızlık onarımı (R-20): meta veri PostgreSQL'den düzeltilir.

    İndekste eksik haberin belgesi meta veriyle oluşturulur (metni geri getirilemez; Elasticsearch yedeği
    gerekir, R-38). Gizlenmiş haber gizli olarak işaretlenir, PostgreSQL'de olmayan haber yeni nesle geçmez.
    """
    await SearchIndex(search_client).ensure_ready()
    for number in (1, 2, 3):
        await add_article(database, trt_feed, number)
    await build_relay(database, search_client).relay_batch()
    # 1: belgesi indeksten kaybolmuş. 2: notu işlenmeden gizlenmiş. 3: PostgreSQL'den silinmiş ama belgesi durmuş.
    lost_id = admin.execute("SELECT id FROM articles WHERE external_id = 'haber-1'").fetchone()
    assert lost_id is not None
    await search_client.delete(index="articles-g1-2026.11.01", id=str(lost_id[0]), refresh=True)
    admin.execute(
        "INSERT INTO users (keycloak_sub, email, role, status) "
        "VALUES ('yonetici', 'yonetici@example.test', 'ADMIN', 'ACTIVE')"
    )
    admin.execute(
        "UPDATE articles SET hidden = true, hidden_at = now(), hidden_by = (SELECT id FROM users) "
        "WHERE external_id = 'haber-2'"
    )
    admin.execute("DELETE FROM articles WHERE external_id = 'haber-3'")
    await add_article(database, trt_feed, 4)
    assert await searchable_titles(search_client) == ["Örnek haber 2", "Örnek haber 3"]

    await build_reindexer(database, search_client).run()

    assert await searchable_titles(search_client) == ["Örnek haber 1", "Örnek haber 4"]
    lost = await source_of(search_client, admin, 1)
    assert "content_tr" not in lost
    hidden = await source_of(search_client, admin, 2)
    assert hidden["hidden"] is True
    assert hidden["content_tr"] == "<p>Tam metin 2</p>"


async def test_reindex_reads_articles_page_by_page(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], search_client: AsyncElasticsearch
) -> None:
    """Haberler sayfa sayfa okunur; sayfa sınırında haber atlanmaz ve iki kez yazılmaz."""
    for number in range(1, 6):
        await add_article(database, trt_feed, number)

    await build_reindexer(database, search_client, page_size=2).run()

    assert await searchable_titles(search_client) == [f"Örnek haber {number}" for number in range(1, 6)]


async def test_reindex_of_an_empty_database_still_switches_generation(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], search_client: AsyncElasticsearch
) -> None:
    """Hiç haber yokken de çalışır; sonradan gelen ilk haber yeni nesle yazılır ve aramaya girer."""
    await SearchIndex(search_client).ensure_ready()

    assert await build_reindexer(database, search_client).run() == 2

    await add_article(database, trt_feed, 1)
    await build_relay(database, search_client).relay_batch()
    assert await index_names(search_client) == ["articles-g2-2026.11.01"]
    assert await searchable_titles(search_client) == ["Örnek haber 1"]


class FailingOnSecondPage(SearchIndex):
    """İkinci sayfada Elasticsearch bir belgeyi reddetmiş gibi davranır."""

    def __init__(self, client: AsyncElasticsearch) -> None:
        super().__init__(client)
        self._pages = 0

    async def write(self, writes: Sequence[DocumentWrite], generation: int) -> dict[UUID, str]:
        self._pages += 1
        if self._pages == 2:
            return {writes[0].metadata.id: "mapper_parsing_exception: örnek hata"}
        return await super().write(writes, generation)


async def test_failed_reindex_leaves_the_active_generation_untouched(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], search_client: AsyncElasticsearch
) -> None:
    """Yarıda kalan yeniden indeksleme aramayı etkilemez: etkin nesil aynı kalır, yarım belgeler aramada görünmez.

    Yeniden çalıştırıldığında yarım kalan nesil silinip baştan yazılır.
    """
    await SearchIndex(search_client).ensure_ready()
    for number in (1, 2, 3):
        await add_article(database, trt_feed, number)
    await build_relay(database, search_client).relay_batch()
    failing = Reindexer(database, ArticleRepository(), FailingOnSecondPage(search_client), page_size=2)

    with pytest.raises(ReindexError, match="Etkin nesil değişmedi"):
        await failing.run()

    assert await SearchIndex(search_client).active_generation() == 1
    # İlk sayfa yeni nesle yazılmıştı; arama yine de her haberi bir kez görür.
    assert await index_names(search_client) == ["articles-g1-2026.11.01", "articles-g2-2026.11.01"]
    assert await searchable_titles(search_client) == ["Örnek haber 1", "Örnek haber 2", "Örnek haber 3"]

    assert await build_reindexer(database, search_client).run() == 2

    assert await index_names(search_client) == ["articles-g2-2026.11.01"]
    assert await searchable_titles(search_client) == ["Örnek haber 1", "Örnek haber 2", "Örnek haber 3"]


class LosingDocuments(SearchIndex):
    """Yazılan belgelerden biri yeni nesilde bulunamıyormuş gibi davranır."""

    async def count_documents(self, generation: int) -> int:
        return await super().count_documents(generation) - 1


async def test_reindex_stops_before_switching_when_document_count_differs(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], search_client: AsyncElasticsearch
) -> None:
    """Yeni nesildeki belge sayısı yazılan haber sayısını tutmuyorsa takma ad taşınmaz."""
    await SearchIndex(search_client).ensure_ready()
    await add_article(database, trt_feed, 1)
    await build_relay(database, search_client).relay_batch()

    with pytest.raises(ReindexError, match="Belge sayısı tutmuyor: 1 haber yazıldı, yeni nesilde 0 belge var"):
        await Reindexer(database, ArticleRepository(), LosingDocuments(search_client)).run()

    assert await SearchIndex(search_client).active_generation() == 1
    assert await searchable_titles(search_client) == ["Örnek haber 1"]


async def test_worker_writes_to_the_new_generation_after_reindex(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], search_client: AsyncElasticsearch
) -> None:
    """Yeniden indekslemeden sonra outbox aktarımı kendiliğinden yeni nesle yazar; eski nesil geri gelmez."""
    await SearchIndex(search_client).ensure_ready()
    await add_article(database, trt_feed, 1)
    relay = build_relay(database, search_client)
    await relay.relay_batch()
    await build_reindexer(database, search_client).run()
    await add_article(database, trt_feed, 2, published_at=JUNE_2023)

    # İşçi yeniden açıldığında yaptığı gibi: önce kurulum, sonra aktarım.
    await SearchIndex(search_client).ensure_ready()
    await relay.relay_batch()

    assert await index_names(search_client) == ["articles-g2-2023.06.01", "articles-g2-2026.11.01"]
    assert await searchable_titles(search_client) == ["Örnek haber 1", "Örnek haber 2"]


async def test_command_reindexes_with_the_configured_stores(
    settings: Settings,
    database: Database,
    admin: psycopg.Connection,
    trt_feed: tuple[UUID, UUID],
    elasticsearch_url: str,
    search_client: AsyncElasticsearch,
) -> None:
    """Komutun kullandığı giriş noktası, ayarlardaki PostgreSQL ve Elasticsearch ile çalışır."""
    await add_article(database, trt_feed, 1)

    new_generation = await reindex.run(replace(settings, es_url=elasticsearch_url))

    assert new_generation == 2
    assert await searchable_titles(search_client) == ["Örnek haber 1"]


def test_command_exits_with_error_code_when_password_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Şifre tanımlı değilse komut hata koduyla çıkar."""
    monkeypatch.delenv("DB_PASSWORD", raising=False)

    with pytest.raises(SystemExit) as exit_info:
        reindex.main()

    assert exit_info.value.code == 2
