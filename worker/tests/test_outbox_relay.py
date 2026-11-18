"""Outbox aktarımının testleri: gerçek PostgreSQL ve gerçek Elasticsearch, işçinin yetkileriyle."""

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

import psycopg
import pytest
from elasticsearch import AsyncElasticsearch, TransportError

from news_worker.articles import ArticleRepository, NewArticle
from news_worker.category_resolver import AssignedCategory, MappingLevel
from news_worker.database import Database
from news_worker.outbox import OutboxRepository
from news_worker.outbox_relay import OutboxRelay, retry_delay_minutes
from news_worker.parsed_article import ItemType, ParsedArticle
from news_worker.search_index import ALIAS, SearchIndex, create_search_client, index_name_for

NOVEMBER = datetime(2026, 11, 13, 13, 40, tzinfo=UTC)
JUNE_2023 = datetime(2023, 6, 6, 16, 2, tzinfo=UTC)


async def add_article(
    database: Database, feed: tuple[UUID, UUID], number: int, published_at: datetime = NOVEMBER
) -> None:
    """Bir haberi işçinin yaptığı gibi kaydeder; outbox notu da kendiliğinden yazılır."""
    article = ParsedArticle(
        external_id=f"haber-{number}",
        url=f"https://example.test/haber-{number}",
        normalized_url=f"https://example.test/haber-{number}",
        title=f"Örnek haber {number}",
        summary=None,
        content=None,
        author=None,
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


def article_id(admin: psycopg.Connection, number: int) -> UUID:
    row = admin.execute("SELECT id FROM articles WHERE external_id = %s", (f"haber-{number}",)).fetchone()
    assert row is not None
    result: UUID = row[0]
    return result


def add_event(admin: psycopg.Connection, target: UUID, operation: str) -> None:
    admin.execute(
        "INSERT INTO outbox_events (article_id, operation, status, next_attempt_at) VALUES (%s, %s, 'PENDING', now())",
        (target, operation),
    )


def hide_articles(admin: psycopg.Connection) -> None:
    """API'nin gizleme işlemini taklit eder: haber gizlenir ve aynı anda DELETE notu yazılır."""
    admin.execute(
        "INSERT INTO users (keycloak_sub, email, role, status) "
        "VALUES ('yonetici', 'yonetici@example.test', 'ADMIN', 'ACTIVE')"
    )
    admin.execute("UPDATE articles SET hidden = true, hidden_at = now(), hidden_by = (SELECT id FROM users)")
    admin.execute(
        "INSERT INTO outbox_events (article_id, operation, status, next_attempt_at) "
        "SELECT id, 'DELETE', 'PENDING', now() FROM articles"
    )


def event_rows(admin: psycopg.Connection) -> list[tuple[str, int, bool]]:
    """Notların durumu, deneme sayısı ve hata yazılıp yazılmadığı; yazılma sırasıyla."""
    return admin.execute("SELECT status, attempts, last_error IS NOT NULL FROM outbox_events ORDER BY id").fetchall()


def build_relay(database: Database, client: AsyncElasticsearch, batch_size: int = 10) -> OutboxRelay:
    return OutboxRelay(
        database,
        OutboxRepository(),
        ArticleRepository(),
        client,
        SearchIndex(client),
        interval_seconds=60,
        batch_size=batch_size,
    )


async def document_exists(client: AsyncElasticsearch, target: UUID, published_at: datetime = NOVEMBER) -> bool:
    return bool(await client.exists(index=index_name_for(published_at), id=str(target)))


@pytest.fixture
async def unreachable_client() -> AsyncElasticsearch:
    """Kimsenin dinlemediği bir adrese bağlanmaya çalışan istemci: "Elasticsearch kapalı" durumu."""
    return create_search_client("http://127.0.0.1:9", "news_worker", "x", request_timeout_seconds=2)


@pytest.mark.parametrize(("attempts", "minutes"), [(0, 1), (1, 5), (2, 15), (3, 15), (40, 15)])
def test_retry_delay_grows_and_then_stays_at_fifteen_minutes(attempts: int, minutes: int) -> None:
    """Reddedilen not 1, 5, 15 dakika sonra, ardından hep 15 dakikada bir yeniden denenir."""
    assert retry_delay_minutes(attempts) == minutes


async def test_new_article_is_written_to_the_search_index(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], search_client: AsyncElasticsearch
) -> None:
    """Kaydedilen haberin notu işlenince haber kendi ayının indeksine yazılır ve not işlenmiş olur."""
    await SearchIndex(search_client).ensure_ready()
    await add_article(database, trt_feed, 1)

    count = await build_relay(database, search_client).relay_batch()

    assert count == 1
    stored = await search_client.get(index="articles-g1-2026.11.01", id=str(article_id(admin, 1)))
    assert stored["_source"]["title_tr"] == "Örnek haber 1"
    assert stored["_source"]["source_code"] == "TRT"
    assert stored["_source"]["categories"] == ["GENERAL"]
    assert event_rows(admin) == [("PROCESSED", 0, False)]


async def test_nothing_happens_when_there_is_no_event(database: Database, search_client: AsyncElasticsearch) -> None:
    """Bekleyen not yoksa tur boş geçer."""
    assert await build_relay(database, search_client).relay_batch() == 0


async def test_two_events_of_one_article_produce_one_document(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], search_client: AsyncElasticsearch
) -> None:
    """Aynı haber için iki not varsa (kategori sonradan eklendi) tek belge oluşur, iki not da işlenir."""
    await SearchIndex(search_client).ensure_ready()
    await add_article(database, trt_feed, 1)
    add_event(admin, article_id(admin, 1), "INDEX")

    await build_relay(database, search_client).relay_batch()

    await search_client.indices.refresh(index=ALIAS)
    assert (await search_client.count(index=ALIAS))["count"] == 1
    assert event_rows(admin) == [("PROCESSED", 0, False), ("PROCESSED", 0, False)]


async def test_processing_the_same_event_twice_changes_nothing(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], search_client: AsyncElasticsearch
) -> None:
    """Tekrarlanabilirlik: belge yazıldıktan sonra not işaretlenemeden işçi çökerse not yeniden işlenir."""
    await SearchIndex(search_client).ensure_ready()
    await add_article(database, trt_feed, 1)
    relay = build_relay(database, search_client)
    await relay.relay_batch()
    # Çökmeyi taklit: belge Elasticsearch'te ama not hâlâ bekliyor görünüyor.
    admin.execute("UPDATE outbox_events SET status = 'PENDING', processed_at = NULL")

    await relay.relay_batch()

    await search_client.indices.refresh(index=ALIAS)
    assert (await search_client.count(index=ALIAS))["count"] == 1
    assert event_rows(admin) == [("PROCESSED", 0, False)]


async def test_batch_size_limits_one_round(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], search_client: AsyncElasticsearch
) -> None:
    """Bir turda en fazla grup büyüklüğü kadar not işlenir; en eski notlar önce."""
    await SearchIndex(search_client).ensure_ready()
    for number in (1, 2, 3):
        await add_article(database, trt_feed, number)

    count = await build_relay(database, search_client, batch_size=2).relay_batch()

    assert count == 2
    assert [status for status, _, _ in event_rows(admin)] == ["PROCESSED", "PROCESSED", "PENDING"]


async def test_hidden_article_is_removed_from_the_search_index(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], search_client: AsyncElasticsearch
) -> None:
    """Gizlenen haberin belgesi silinir (FG-AR-09); belge az önce yazılmış olsa da bulunur."""
    await SearchIndex(search_client).ensure_ready()
    await add_article(database, trt_feed, 1)
    relay = build_relay(database, search_client)
    await relay.relay_batch()
    hide_articles(admin)

    await relay.relay_batch()

    assert not await document_exists(search_client, article_id(admin, 1))
    assert event_rows(admin) == [("PROCESSED", 0, False), ("PROCESSED", 0, False)]


async def test_article_hidden_before_its_first_event_is_never_indexed(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], search_client: AsyncElasticsearch
) -> None:
    """Haber, ilk notu işlenmeden gizlenirse indekse hiç yazılmaz; INDEX notu da işlenmiş sayılır."""
    await SearchIndex(search_client).ensure_ready()
    await add_article(database, trt_feed, 1)
    hide_articles(admin)

    await build_relay(database, search_client).relay_batch()

    assert not await document_exists(search_client, article_id(admin, 1))
    assert event_rows(admin) == [("PROCESSED", 0, False), ("PROCESSED", 0, False)]


async def test_event_of_a_deleted_article_is_processed_without_any_index(
    database: Database, admin: psycopg.Connection, search_client: AsyncElasticsearch
) -> None:
    """Silinmiş bir haberin notu, henüz hiç indeks yokken de hatasız işlenir: silinecek belge yoktur."""
    await SearchIndex(search_client).ensure_ready()
    add_event(admin, UUID("019a0000-0000-7000-8000-000000000099"), "DELETE")

    await build_relay(database, search_client).relay_batch()

    assert event_rows(admin) == [("PROCESSED", 0, False)]


async def test_late_delete_event_does_not_remove_a_visible_article(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], search_client: AsyncElasticsearch
) -> None:
    """Karar haberin o anki durumuna göre verilir: haber görünürse, eski bir DELETE notu belgeyi silmez.

    Gizlenip geri açılan bir haberin DELETE notu geç işlenirse haber aramadan kaybolmamalıdır.
    """
    await SearchIndex(search_client).ensure_ready()
    await add_article(database, trt_feed, 1)
    add_event(admin, article_id(admin, 1), "DELETE")

    await build_relay(database, search_client).relay_batch()

    assert await document_exists(search_client, article_id(admin, 1))


async def test_rejected_document_is_retried_later_and_others_are_processed(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], search_client: AsyncElasticsearch
) -> None:
    """Elasticsearch tek bir belgeyi reddederse yalnızca onun notu ertelenir; gruptaki diğerleri işlenir."""
    await SearchIndex(search_client).ensure_ready()
    # Haziran 2023 indeksi kapatılır: bu indekse yazılan belge reddedilir, Kasım'a yazılan edilmez.
    await search_client.indices.create(index=index_name_for(JUNE_2023))
    await search_client.indices.close(index=index_name_for(JUNE_2023))
    await add_article(database, trt_feed, 1, published_at=JUNE_2023)
    await add_article(database, trt_feed, 2)

    await build_relay(database, search_client).relay_batch()

    assert await document_exists(search_client, article_id(admin, 2))
    assert event_rows(admin) == [("PENDING", 1, True), ("PROCESSED", 0, False)]
    row = admin.execute(
        "SELECT last_error, next_attempt_at BETWEEN now() AND now() + interval '1 minute' "
        "FROM outbox_events WHERE status = 'PENDING'"
    ).fetchone()
    assert row is not None
    assert "index_closed_exception" in row[0]
    assert row[1] is True


async def test_events_wait_untouched_while_elasticsearch_is_down(
    database: Database,
    admin: psycopg.Connection,
    trt_feed: tuple[UUID, UUID],
    search_client: AsyncElasticsearch,
    unreachable_client: AsyncElasticsearch,
) -> None:
    """Elasticsearch kapalıyken notlar olduğu gibi bekler; geri geldiğinde aktarılır (FOG-09)."""
    await SearchIndex(search_client).ensure_ready()
    await add_article(database, trt_feed, 1)

    with pytest.raises(TransportError):
        await build_relay(database, unreachable_client).relay_batch()
    await unreachable_client.close()

    assert event_rows(admin) == [("PENDING", 0, False)]

    await build_relay(database, search_client).relay_batch()

    assert await document_exists(search_client, article_id(admin, 1))
    assert event_rows(admin) == [("PROCESSED", 0, False)]


async def wait_until_no_event_is_pending(admin: psycopg.Connection, timeout_seconds: float = 10) -> None:
    async with asyncio.timeout(timeout_seconds):
        # Beklenen değişiklik veritabanında oluşur; haber verecek bir Event yoktur, bu yüzden yoklanır.
        pending_query = "SELECT count(*) FROM outbox_events WHERE status = 'PENDING'"
        while admin.execute(pending_query).fetchone() != (0,):  # noqa: ASYNC110
            await asyncio.sleep(0.05)


async def test_loop_continues_without_waiting_while_batches_are_full(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], search_client: AsyncElasticsearch
) -> None:
    """Grup dolu geldikçe döngü beklemez: 5 not, 2'şerli gruplarla, 60 saniyelik aralık beklenmeden biter."""
    for number in range(1, 6):
        await add_article(database, trt_feed, number)
    stop = asyncio.Event()

    task = asyncio.create_task(build_relay(database, search_client, batch_size=2).run(stop))
    await wait_until_no_event_is_pending(admin)
    stop.set()
    await asyncio.wait_for(task, timeout=5)

    assert [status for status, _, _ in event_rows(admin)] == ["PROCESSED"] * 5


async def test_loop_sets_up_the_index_before_the_first_document(
    database: Database, admin: psycopg.Connection, trt_feed: tuple[UUID, UUID], search_client: AsyncElasticsearch
) -> None:
    """Döngü, ilk belgeden önce şablonu kendisi kurar; aylık indeks doğru analizörlerle açılır."""
    await add_article(database, trt_feed, 1)
    stop = asyncio.Event()

    task = asyncio.create_task(build_relay(database, search_client).run(stop))
    await wait_until_no_event_is_pending(admin)
    stop.set()
    await asyncio.wait_for(task, timeout=5)

    mapping = await search_client.indices.get_mapping(index="articles-g1-2026.11.01")
    properties = mapping["articles-g1-2026.11.01"]["mappings"]["properties"]
    assert properties["title_tr"]["analyzer"] == "turkish_article"
    assert properties["title_tr"]["fields"]["folded"]["analyzer"] == "turkish_folded"


async def test_loop_survives_elasticsearch_outage(
    database: Database,
    admin: psycopg.Connection,
    trt_feed: tuple[UUID, UUID],
    unreachable_client: AsyncElasticsearch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Elasticsearch kapalıyken döngü çökmez; uyarı yazar ve durdurma istenince düzgün biter."""
    await add_article(database, trt_feed, 1)
    stop = asyncio.Event()
    relay = OutboxRelay(
        database,
        OutboxRepository(),
        ArticleRepository(),
        unreachable_client,
        SearchIndex(unreachable_client),
        interval_seconds=0.05,
        batch_size=10,
    )

    with caplog.at_level(logging.WARNING, logger="news_worker.outbox_relay"):
        task = asyncio.create_task(relay.run(stop))
        async with asyncio.timeout(20):
            while "Elasticsearch'e ulaşılamadı" not in caplog.text:  # noqa: ASYNC110
                await asyncio.sleep(0.05)
        stop.set()
        await asyncio.wait_for(task, timeout=20)
    await unreachable_client.close()

    assert event_rows(admin) == [("PENDING", 0, False)]
