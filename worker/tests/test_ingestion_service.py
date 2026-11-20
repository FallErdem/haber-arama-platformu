"""Toplama akışının testleri.

Veritabanı gerçektir (PostgreSQL, bütün geçiş betikleri uygulanmış, işçinin kendi kullanıcısı);
kaynak siteler sahtedir (respx) ve yanıt olarak kaydedilmiş gerçek besleme örnekleri verilir.
"""

from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import psycopg
import pytest
import respx

from news_worker.database import Database
from news_worker.feed_fetcher import FeedFetcher, create_http_client
from news_worker.feed_reader import FeedReader, FeedReadResult
from news_worker.feeds import DueFeed, FeedRepository
from news_worker.ingestion_service import (
    FEED_AUTO_DISABLED_ACTION,
    MAX_CONSECUTIVE_FAILURES,
    IngestionService,
)
from news_worker.parsed_article import ItemType, ParsedArticle
from news_worker.rate_limiter import SourceRateLimiter

FIXTURES = Path(__file__).parent / "fixtures" / "feeds"
NOW = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)


async def no_sleep(seconds: float) -> None:
    """İstek sınırlayıcının beklemesi testlerde atlanır."""


@pytest.fixture
async def fetcher() -> AsyncIterator[FeedFetcher]:
    async with create_http_client("HaberAramaPlatformuTest/0.1", timeout_seconds=5) as client:
        yield FeedFetcher(client, total_timeout_seconds=5)


def build_service(database: Database, fetcher: FeedFetcher, reader: FeedReader) -> IngestionService:
    return IngestionService(database, fetcher, reader, SourceRateLimiter(sleep=no_sleep), clock=lambda: NOW)


@pytest.fixture
def service(database: Database, fetcher: FeedFetcher) -> IngestionService:
    return build_service(database, fetcher, FeedReader())


async def due_feed(database: Database, source_code: str, name: str) -> DueFeed:
    """Beslemeyi, zamanlayıcının göreceği haliyle (güncel ETag ve ayarlarla) veritabanından okur."""
    async with await database.connect() as connection:
        feeds = await FeedRepository().find_due(connection, limit=1000)
    return next(feed for feed in feeds if feed.source_code == source_code and feed.name == name)


def fixture_body(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def feed_state(admin: psycopg.Connection, feed: DueFeed) -> dict[str, Any]:
    """Beslemenin toplama sonrası durumu. Bir sonraki okuma zamanı "kaç dakika sonra" olarak verilir."""
    row = admin.execute(
        "SELECT consecutive_failures, enabled, disabled_reason, last_error, etag, last_modified, "
        "last_success_at IS NOT NULL, round(extract(epoch FROM next_fetch_at - now()) / 60)::int "
        "FROM feeds WHERE id = %s",
        (feed.id,),
    ).fetchone()
    assert row is not None
    keys = (
        "consecutive_failures",
        "enabled",
        "disabled_reason",
        "last_error",
        "etag",
        "last_modified",
        "has_succeeded",
        "next_fetch_in_minutes",
    )
    return dict(zip(keys, row, strict=True))


def last_run(admin: psycopg.Connection, feed: DueFeed) -> dict[str, Any]:
    row = admin.execute(
        "SELECT trigger, status, finished_at IS NOT NULL, http_status, final_url, items_received, items_new, "
        "items_duplicate, items_failed, error_message FROM ingestion_runs WHERE feed_id = %s "
        "ORDER BY started_at DESC, id DESC LIMIT 1",
        (feed.id,),
    ).fetchone()
    assert row is not None
    keys = (
        "trigger",
        "status",
        "is_finished",
        "http_status",
        "final_url",
        "items_received",
        "items_new",
        "items_duplicate",
        "items_failed",
        "error_message",
    )
    return dict(zip(keys, row, strict=True))


def count(admin: psycopg.Connection, table: str) -> int:
    row = admin.execute(f"SELECT count(*) FROM {table}").fetchone()
    assert row is not None
    result: int = row[0]
    return result


def auto_disabled_events(admin: psycopg.Connection, feed: DueFeed) -> list[tuple[Any, ...]]:
    """Beslemeye ait "otomatik devre dışı" audit kayıtları. Audit kayıtları silinemediği için beslemeye göre süzülür."""
    return admin.execute(
        "SELECT actor_type, actor_user_id, target_type, result, details FROM audit_events "
        "WHERE action = %s AND target_id = %s",
        (FEED_AUTO_DISABLED_ACTION, feed.id),
    ).fetchall()


def make_due_again(admin: psycopg.Connection) -> None:
    """Bütün beslemelerin okuma zamanını şimdiye çeker (elle toplamanın yaptığı gibi)."""
    admin.execute("UPDATE feeds SET next_fetch_at = now()")


async def test_articles_of_a_feed_are_stored(
    service: IngestionService, database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """Başarılı okuma: haberler kaydedilir, okuma kaydı sayılarla birlikte yazılır, besleme ileri atılır."""
    feed = await due_feed(database, "TRT", "gundem")
    respx_mock.get(feed.url).respond(200, content=fixture_body("trt-gundem.xml"), headers={"ETag": '"v1"'})

    await service.ingest(feed)

    assert count(admin, "articles") == 3
    assert last_run(admin, feed) == {
        "trigger": "SCHEDULED",
        "status": "SUCCEEDED",
        "is_finished": True,
        "http_status": 200,
        "final_url": feed.url,
        "items_received": 3,
        "items_new": 3,
        "items_duplicate": 0,
        "items_failed": 0,
        "error_message": None,
    }
    assert feed_state(admin, feed) == {
        "consecutive_failures": 0,
        "enabled": True,
        "disabled_reason": None,
        "last_error": None,
        "etag": '"v1"',
        "last_modified": None,
        "has_succeeded": True,
        # TRT beslemelerinin sıklığı 15 dakikadır.
        "next_fetch_in_minutes": 15,
    }


async def test_stored_articles_carry_source_feed_and_language(
    service: IngestionService, database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """Haberler doğru kaynağa, beslemeye ve dile bağlanır; toplanma zamanı kaydedilir."""
    feed = await due_feed(database, "TRT", "gundem")
    respx_mock.get(feed.url).respond(200, content=fixture_body("trt-gundem.xml"))

    await service.ingest(feed)

    rows = admin.execute("SELECT DISTINCT source_id, feed_id, language, fetched_at FROM articles").fetchall()
    assert rows == [(feed.source_id, feed.id, "tr", NOW)]


async def test_topic_feed_assigns_feed_category(
    service: IngestionService, database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """Konuya özel beslemenin (TRT `gundem`) haberleri beslemenin kategorisini alır."""
    feed = await due_feed(database, "TRT", "gundem")
    respx_mock.get(feed.url).respond(200, content=fixture_body("trt-gundem.xml"))

    await service.ingest(feed)

    rows = admin.execute(
        "SELECT c.code, ac.mapping_level, count(*) FROM article_categories ac "
        "JOIN categories c ON c.id = ac.category_id GROUP BY c.code, ac.mapping_level"
    ).fetchall()
    assert rows == [("GENERAL", "FEED", 3)]


async def test_mixed_feed_assigns_categories_from_article_urls_and_reads_custom_images(
    service: IngestionService, database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """CNN Türk `all`: kategori haber adresinden bulunur; görsel veritabanındaki alan eşlemesiyle okunur."""
    feed = await due_feed(database, "CNNTURK", "all")
    respx_mock.get(feed.url).respond(200, content=fixture_body("cnnturk-all.xml"))

    await service.ingest(feed)

    categories = admin.execute(
        "SELECT a.item_type, c.code, ac.mapping_level FROM articles a "
        "JOIN article_categories ac ON ac.article_id = a.id JOIN categories c ON c.id = ac.category_id "
        "ORDER BY a.published_at DESC"
    ).fetchall()
    assert categories == [("VIDEO", "WORLD", "ITEM"), ("ARTICLE", "ECONOMY", "ITEM"), ("ARTICLE", "GENERAL", "ITEM")]
    # Örnekteki üç haberden ikisinde <image> etiketi var.
    assert count(admin, "media") == 2


async def test_cnnturk_times_are_read_with_the_source_time_zone(
    service: IngestionService, database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """CNN Türk'ün "GMT" yazan saatleri veritabanındaki ayarla (V15) Türkiye saati olarak kaydedilir."""
    feed = await due_feed(database, "CNNTURK", "all")
    respx_mock.get(feed.url).respond(200, content=fixture_body("cnnturk-all.xml"))

    await service.ingest(feed)

    rows = admin.execute("SELECT published_at FROM articles ORDER BY published_at DESC").fetchall()
    # Beslemede 17:05:15, 17:01:24 ve 16:46:44 "GMT" yazıyor; bunlar Türkiye saatidir (UTC+3).
    assert [row[0].astimezone(UTC) for row in rows] == [
        datetime(2026, 11, 13, 14, 5, 15, tzinfo=UTC),
        datetime(2026, 11, 13, 14, 1, 24, tzinfo=UTC),
        datetime(2026, 11, 13, 13, 46, 44, tzinfo=UTC),
    ]


async def test_repeated_articles_are_counted_as_duplicates(
    service: IngestionService, database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """Aynı besleme ikinci kez okunduğunda haberler yeniden kaydedilmez; tekrar olarak sayılır (FG-VT-04)."""
    feed = await due_feed(database, "TRT", "gundem")
    respx_mock.get(feed.url).respond(200, content=fixture_body("trt-gundem.xml"))
    await service.ingest(feed)

    await service.ingest(feed)

    assert count(admin, "articles") == 3
    assert count(admin, "outbox_events") == 3
    run = last_run(admin, feed)
    assert (run["status"], run["items_new"], run["items_duplicate"]) == ("SUCCEEDED", 0, 3)
    assert count(admin, "ingestion_runs") == 2


async def test_article_seen_later_in_breaking_feed_also_gets_breaking_category(
    service: IngestionService, database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """Aynı haberler önce `gundem`, sonra `sondakika` beslemesinden gelir; ikisinin de kategorisini taşırlar."""
    topic_feed = await due_feed(database, "TRT", "gundem")
    breaking_feed = await due_feed(database, "TRT", "sondakika")
    respx_mock.get(topic_feed.url).respond(200, content=fixture_body("trt-gundem.xml"))
    respx_mock.get(breaking_feed.url).respond(200, content=fixture_body("trt-gundem.xml"))
    await service.ingest(topic_feed)

    await service.ingest(breaking_feed)

    assert count(admin, "articles") == 3
    run = last_run(admin, breaking_feed)
    assert (run["items_new"], run["items_duplicate"]) == (0, 3)
    rows = admin.execute(
        "SELECT c.code, ac.mapping_level, count(*) FROM article_categories ac "
        "JOIN categories c ON c.id = ac.category_id GROUP BY c.code, ac.mapping_level ORDER BY c.code"
    ).fetchall()
    assert rows == [("BREAKING", "FEED", 3), ("GENERAL", "FEED", 3)]


async def test_stored_validators_are_sent_and_not_modified_is_recorded(
    service: IngestionService, database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """İlk okumada saklanan ETag ikinci okumada gönderilir; 304 gelirse içerik işlenmez, okuma başarılı sayılır."""
    feed = await due_feed(database, "TRT", "gundem")
    route = respx_mock.get(feed.url)
    route.side_effect = [
        httpx.Response(200, content=fixture_body("trt-gundem.xml"), headers={"ETag": '"v1"'}),
        httpx.Response(304),
    ]
    await service.ingest(feed)
    make_due_again(admin)

    await service.ingest(await due_feed(database, "TRT", "gundem"))

    assert route.calls.last.request.headers["If-None-Match"] == '"v1"'
    run = last_run(admin, feed)
    assert (run["status"], run["http_status"], run["items_received"]) == ("NOT_MODIFIED", 304, None)
    state = feed_state(admin, feed)
    assert (state["etag"], state["consecutive_failures"], state["next_fetch_in_minutes"]) == ('"v1"', 0, 15)
    assert count(admin, "articles") == 3


async def test_failed_download_is_recorded_and_retried_after_one_minute(
    service: IngestionService, database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """Başarısız okuma kaydedilir; ilk hatadan sonra 1 dakika sonra yeniden denenir."""
    feed = await due_feed(database, "TRT", "gundem")
    respx_mock.get(feed.url).respond(500)

    await service.ingest(feed)

    run = last_run(admin, feed)
    assert (run["status"], run["is_finished"], run["http_status"]) == ("FAILED", True, 500)
    assert run["error_message"] == "Beklenmeyen yanıt (HTTP 500)"
    state = feed_state(admin, feed)
    assert state["consecutive_failures"] == 1
    assert state["last_error"] == "Beklenmeyen yanıt (HTTP 500)"
    assert state["enabled"] is True
    assert state["next_fetch_in_minutes"] == 1
    assert count(admin, "articles") == 0


async def test_retry_delays_grow_and_fifth_failure_disables_the_feed(
    service: IngestionService, database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """Yeniden deneme 1, 5, 15, 15 dakika sonra yapılır; 5. hatada besleme otomatik devre dışı kalır (FG-YP-07)."""
    feed = await due_feed(database, "TRT", "gundem")
    respx_mock.get(feed.url).respond(503)
    events_before = len(auto_disabled_events(admin, feed))

    delays = []
    for _ in range(MAX_CONSECUTIVE_FAILURES - 1):
        await service.ingest(feed)
        delays.append(feed_state(admin, feed)["next_fetch_in_minutes"])
    assert delays == [1, 5, 15, 15]
    assert feed_state(admin, feed)["enabled"] is True
    assert len(auto_disabled_events(admin, feed)) == events_before

    await service.ingest(feed)

    state = feed_state(admin, feed)
    assert (state["consecutive_failures"], state["enabled"], state["disabled_reason"]) == (5, False, "AUTO")
    events = auto_disabled_events(admin, feed)
    assert len(events) == events_before + 1
    assert events[-1] == (
        "SYSTEM",
        None,
        "FEED",
        "SUCCESS",
        {"consecutive_failures": 5, "last_error": "Beklenmeyen yanıt (HTTP 503)"},
    )
    assert last_run(admin, feed)["status"] == "FAILED"


async def test_disabled_feed_does_not_affect_other_feeds_of_the_source(
    service: IngestionService, database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """Bir beslemenin devre dışı kalması kaynağın diğer beslemelerini etkilemez (FG-YP-07)."""
    feed = await due_feed(database, "TRT", "gundem")
    respx_mock.get(feed.url).respond(503)

    for _ in range(MAX_CONSECUTIVE_FAILURES):
        await service.ingest(feed)

    rows = admin.execute(
        "SELECT f.enabled, count(*) FROM feeds f JOIN sources s ON s.id = f.source_id "
        "WHERE s.code = 'TRT' GROUP BY f.enabled ORDER BY f.enabled"
    ).fetchall()
    assert rows == [(False, 1), (True, 17)]


async def test_success_resets_the_failure_counter(
    service: IngestionService, database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """Sayaç "art arda" hataları sayar: araya giren başarılı okuma sayacı ve son hatayı sıfırlar."""
    feed = await due_feed(database, "TRT", "gundem")
    route = respx_mock.get(feed.url)
    route.side_effect = [
        httpx.Response(500),
        httpx.Response(500),
        httpx.Response(200, content=fixture_body("trt-gundem.xml")),
    ]
    await service.ingest(feed)
    await service.ingest(feed)
    assert feed_state(admin, feed)["consecutive_failures"] == 2

    await service.ingest(feed)

    state = feed_state(admin, feed)
    assert (state["consecutive_failures"], state["last_error"]) == (0, None)


async def test_access_denial_is_a_failure_and_is_not_bypassed(
    service: IngestionService, database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """403 aşılmaya çalışılmaz: tek istek atılır ve başarısız okuma olarak kaydedilir (FG-VT-06)."""
    feed = await due_feed(database, "NTV", "turkiye")
    route = respx_mock.get(feed.url).respond(403)

    await service.ingest(feed)

    assert route.call_count == 1
    run = last_run(admin, feed)
    assert (run["status"], run["http_status"]) == ("FAILED", 403)
    assert run["error_message"] == "Kaynak erişimi reddetti (HTTP 403)"
    assert feed_state(admin, feed)["consecutive_failures"] == 1


@pytest.mark.parametrize(
    ("headers", "expected_minutes"),
    [({"Retry-After": "3600"}, 60), ({"Retry-After": "30"}, 15), ({}, 15)],
    ids=["longer-than-interval", "shorter-than-interval", "not-given"],
)
async def test_rate_limited_feed_is_postponed_without_counting_a_failure(
    service: IngestionService,
    database: Database,
    admin: psycopg.Connection,
    respx_mock: respx.MockRouter,
    headers: dict[str, str],
    expected_minutes: int,
) -> None:
    """429: okuma, beslemenin sıklığı ile kaynağın istediği süreden uzun olanı kadar ertelenir; sayaç artmaz."""
    feed = await due_feed(database, "TRT", "gundem")
    respx_mock.get(feed.url).respond(429, headers=headers)

    await service.ingest(feed)

    state = feed_state(admin, feed)
    assert state["consecutive_failures"] == 0
    assert state["next_fetch_in_minutes"] == expected_minutes
    assert state["last_error"] == "Kaynak istek sınırının aşıldığını bildirdi (HTTP 429)"
    run = last_run(admin, feed)
    assert (run["status"], run["http_status"]) == ("FAILED", 429)


async def test_unrecognized_content_is_a_failure(
    service: IngestionService, database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """200 ile besleme yerine bir HTML sayfası gelirse okuma başarısız sayılır."""
    feed = await due_feed(database, "TRT", "gundem")
    respx_mock.get(feed.url).respond(200, content=b"<html><body>Bakimdayiz</body></html>")

    await service.ingest(feed)

    run = last_run(admin, feed)
    assert (run["status"], run["http_status"]) == ("FAILED", 200)
    assert run["error_message"] == "İçerik RSS veya Atom olarak tanınamadı"
    assert feed_state(admin, feed)["consecutive_failures"] == 1


async def test_items_missing_required_fields_are_counted_as_failed(
    service: IngestionService, database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """Zorunlu alanı eksik haber atlanır ve sayılır; diğer haberler kaydedilir, okuma başarılıdır."""
    feed = await due_feed(database, "TRT", "gundem")
    body = (
        b'<rss version="2.0"><channel>'
        b"<item><guid>a</guid><title>Tam haber</title><link>https://example.test/a</link>"
        b"<pubDate>Sun, 15 Nov 2026 10:00:00 GMT</pubDate></item>"
        b"<item><guid>b</guid><title>Tarihsiz haber</title><link>https://example.test/b</link></item>"
        b"</channel></rss>"
    )
    respx_mock.get(feed.url).respond(200, content=body)

    await service.ingest(feed)

    run = last_run(admin, feed)
    assert (run["status"], run["items_received"], run["items_new"], run["items_failed"]) == ("SUCCEEDED", 2, 1, 1)
    assert count(admin, "articles") == 1


class StubReader(FeedReader):
    """Verilen haberleri döndüren ya da hata fırlatan sahte okuyucu."""

    def __init__(self, articles: tuple[ParsedArticle, ...] = (), error: Exception | None = None) -> None:
        self._articles = articles
        self._error = error

    def read(self, body: bytes, field_mapping: Any = None, feed_time_zone: str | None = None) -> FeedReadResult:
        if self._error is not None:
            raise self._error
        return FeedReadResult(articles=self._articles, skipped_count=0)


def parsed_article(external_id: str, title: str) -> ParsedArticle:
    return ParsedArticle(
        external_id=external_id,
        url=f"https://example.test/{external_id}",
        normalized_url=f"https://example.test/{external_id}",
        title=title,
        summary=None,
        content=None,
        author=None,
        published_at=NOW,
        item_type=ItemType.ARTICLE,
        image_urls=(),
        source_categories=(),
    )


async def test_article_that_cannot_be_stored_does_not_stop_the_others(
    fetcher: FeedFetcher, database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """Bir haber kaydedilemezse (PostgreSQL metinde NULL karakterini kabul etmez) yalnızca o atlanır."""
    feed = await due_feed(database, "TRT", "gundem")
    respx_mock.get(feed.url).respond(200, content=b"-")
    articles = (
        parsed_article("a", "İlk haber"),
        parsed_article("b", "Bozuk\x00haber"),
        parsed_article("c", "Son haber"),
    )

    await build_service(database, fetcher, StubReader(articles)).ingest(feed)

    assert admin.execute("SELECT title FROM articles ORDER BY external_id").fetchall() == [
        ("İlk haber",),
        ("Son haber",),
    ]
    run = last_run(admin, feed)
    assert (run["status"], run["items_new"], run["items_failed"]) == ("SUCCEEDED", 2, 1)


async def test_unexpected_error_is_recorded_as_a_failed_run(
    fetcher: FeedFetcher, database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """Öngörülmeyen bir hata okumayı RUNNING durumunda bırakmaz: başarısız okuma olarak kaydedilir."""
    feed = await due_feed(database, "TRT", "gundem")
    respx_mock.get(feed.url).respond(200, content=b"-")

    await build_service(database, fetcher, StubReader(error=RuntimeError("beklenmeyen"))).ingest(feed)

    run = last_run(admin, feed)
    assert (run["status"], run["is_finished"], run["error_message"]) == (
        "FAILED",
        True,
        "Beklenmeyen hata: RuntimeError",
    )
    assert feed_state(admin, feed)["consecutive_failures"] == 1


async def test_manually_disabled_feed_is_not_marked_as_auto_disabled(
    service: IngestionService, database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """Okuma sürerken yönetici beslemeyi elle kapattıysa neden `MANUAL` kalır ve audit kaydı yazılmaz."""
    feed = await due_feed(database, "TRT", "gundem")
    respx_mock.get(feed.url).respond(500)
    admin.execute(
        "UPDATE feeds SET enabled = false, disabled_reason = 'MANUAL', consecutive_failures = 4 WHERE id = %s",
        (feed.id,),
    )
    events_before = len(auto_disabled_events(admin, feed))

    await service.ingest(feed)

    state = feed_state(admin, feed)
    assert (state["consecutive_failures"], state["enabled"], state["disabled_reason"]) == (5, False, "MANUAL")
    assert len(auto_disabled_events(admin, feed)) == events_before


async def test_request_waits_for_the_source_rate_limit(
    database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """Aynı kaynağın iki beslemesi art arda okunurken kaynağın istek aralığı kadar beklenir (FG-VT-05)."""
    sleeps: list[float] = []

    async def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    first = await due_feed(database, "GLOBALVOICES", "main")
    second = replace(first, url="https://globalvoices.org/ikinci-besleme/")
    respx_mock.get(first.url).respond(304)
    respx_mock.get(second.url).respond(304)
    # Saat hiç ilerlemez: ikinci istek, aralığın tamamı kadar beklemek zorundadır.
    limiter = SourceRateLimiter(clock=lambda: 0.0, sleep=record_sleep)
    async with create_http_client("HaberAramaPlatformuTest/0.1", timeout_seconds=5) as client:
        service = IngestionService(database, FeedFetcher(client, total_timeout_seconds=5), FeedReader(), limiter)

        await service.ingest(first)
        await service.ingest(second)

    # Global Voices'ın istek aralığı 10 saniyedir (robots.txt: Crawl-delay: 10).
    assert sleeps == [10]


# --- Elle toplama (FG-YP-08) ------------------------------------------------------------------------


def request_manual_fetch(admin: psycopg.Connection, feed: DueFeed, requested_at: str = "now()") -> None:
    """API'nin elle toplama isteğinde yaptığını yapar: isteğin zamanını yazar, okuma zamanını şimdiye çeker."""
    admin.execute(
        f"UPDATE feeds SET manual_fetch_requested_at = {requested_at}, next_fetch_at = now() WHERE id = %s",
        (feed.id,),
    )


def manual_request_is_pending(admin: psycopg.Connection, feed: DueFeed) -> bool:
    row = admin.execute("SELECT manual_fetch_requested_at IS NOT NULL FROM feeds WHERE id = %s", (feed.id,)).fetchone()
    assert row is not None
    pending: bool = row[0]
    return pending


async def test_manual_fetch_is_recorded_as_manual_and_the_request_is_consumed(
    service: IngestionService, database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """Elle istenen okuma MANUAL olarak kaydedilir; okuma bitince istek silinir ve sıklık normale döner."""
    feed = await due_feed(database, "TRT", "gundem")
    request_manual_fetch(admin, feed)
    respx_mock.get(feed.url).respond(200, content=fixture_body("trt-gundem.xml"))

    await service.ingest(await due_feed(database, "TRT", "gundem"))

    assert last_run(admin, feed)["trigger"] == "MANUAL"
    assert manual_request_is_pending(admin, feed) is False
    assert feed_state(admin, feed)["next_fetch_in_minutes"] == 15


async def test_manual_request_is_consumed_by_a_failed_read(
    service: IngestionService, database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """Başarısız okuma da isteği karşılar: istek silinir, besleme normal yeniden deneme kuralına girer."""
    feed = await due_feed(database, "TRT", "gundem")
    request_manual_fetch(admin, feed)
    respx_mock.get(feed.url).respond(500)

    await service.ingest(await due_feed(database, "TRT", "gundem"))

    assert last_run(admin, feed)["trigger"] == "MANUAL"
    assert manual_request_is_pending(admin, feed) is False
    assert feed_state(admin, feed)["next_fetch_in_minutes"] == 1


async def test_manual_request_arriving_during_a_read_is_not_lost(
    service: IngestionService, database: Database, admin: psycopg.Connection, respx_mock: respx.MockRouter
) -> None:
    """Okuma sürerken gelen yeni istek kaybolmaz: istek kalır ve besleme hemen yeniden okunur."""
    request_manual_fetch(admin, await due_feed(database, "TRT", "gundem"), "now() - interval '1 minute'")
    feed = await due_feed(database, "TRT", "gundem")
    # Okuma başladıktan sonra yönetici yeniden "Şimdi topla"ya basar.
    request_manual_fetch(admin, feed)
    respx_mock.get(feed.url).respond(200, content=fixture_body("trt-gundem.xml"))

    await service.ingest(feed)

    assert manual_request_is_pending(admin, feed) is True
    assert feed_state(admin, feed)["next_fetch_in_minutes"] == 0
    assert (await due_feed(database, "TRT", "gundem")).manual_fetch_requested_at is not None
