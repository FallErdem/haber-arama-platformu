import asyncio
import json
import logging
from dataclasses import replace

import httpx
import psycopg
import pytest
import respx
from elasticsearch import AsyncElasticsearch

from news_worker import app
from news_worker.config import Settings
from news_worker.logging_config import JsonFormatter, configure_logging
from news_worker.search_index import template_name_for


async def test_worker_finds_tables_ingests_due_feeds_relays_outbox_and_stops_on_request(
    settings: Settings,
    admin: psycopg.Connection,
    elasticsearch_url: str,
    search_client: AsyncElasticsearch,
    respx_mock: respx.MockRouter,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """İşçi tabloları bulur, zamanı gelen beslemeleri toplar, bekleyen outbox notunu aktarır ve
    durdurma istenince düzgünce kapanır."""
    caplog.set_level(logging.INFO)
    # Elasticsearch istemcisi de httpx kullanır; test Elasticsearch'üne giden istekler taklit edilmez.
    elasticsearch = httpx.URL(elasticsearch_url)
    respx_mock.route(host=elasticsearch.host, port=elasticsearch.port).pass_through()
    # Gerçek sitelere gidilmez: geri kalan her istek sahte bir "değişmedi" yanıtı alır.
    feed_requests = respx_mock.route().respond(304)
    # Bekleyen bir not: haberi kayıtlı olmadığı için işlenmesi "belgesi yoksa bir şey yapma" demektir.
    admin.execute(
        "INSERT INTO outbox_events (article_id, operation, status, next_attempt_at) "
        "VALUES ('019a0000-0000-7000-8000-000000000099', 'DELETE', 'PENDING', now())"
    )
    # Yalnızca iki ayrı kaynağın birer beslemesinin zamanı gelmiş olsun; aynı kaynağa ikinci
    # istek atılmadığı için istek aralığı beklenmez ve test hızlı biter.
    admin.execute("UPDATE feeds SET next_fetch_at = now() + interval '1 hour'")
    admin.execute(
        "UPDATE feeds SET next_fetch_at = now() WHERE url IN "
        "('https://www.trthaber.com/gundem_articles.rss', 'https://globalvoices.org/feed/')"
    )
    stop = asyncio.Event()
    # 18080: testte sağlık adresi için sabit bir port; 8080 başka bir süreçte dolu olabilir.
    worker_settings = replace(settings, health_port=18080, es_url=elasticsearch_url, outbox_interval_seconds=0.05)
    task = asyncio.create_task(app.run(worker_settings, stop))

    await asyncio.sleep(0.5)
    async with asyncio.timeout(10):
        pending_query = "SELECT count(*) FROM outbox_events WHERE status = 'PENDING'"
        while admin.execute(pending_query).fetchone() != (0,):  # noqa: ASYNC110
            await asyncio.sleep(0.05)
    stop.set()
    async with asyncio.timeout(5):
        await task

    messages = [record.getMessage() for record in caplog.records]
    assert "Tablolar hazır; zamanlayıcı başlıyor" in messages
    assert "Okuma zamanı gelmiş besleme sayısı: 2" in messages
    assert messages[-1] == "İşçi durdu"
    runs = admin.execute(
        "SELECT f.url, r.status FROM ingestion_runs r JOIN feeds f ON f.id = r.feed_id ORDER BY f.url"
    ).fetchall()
    assert runs == [
        ("https://globalvoices.org/feed/", "NOT_MODIFIED"),
        ("https://www.trthaber.com/gundem_articles.rss", "NOT_MODIFIED"),
    ]
    # İşçi kendini ayarlardaki adla tanıtmıştır.
    assert feed_requests.calls.last.request.headers["User-Agent"] == settings.http_user_agent
    # Outbox aktarımı da çalışmıştır: bekleyen not işlenmiş, indeks şablonu kurulmuştur.
    assert admin.execute("SELECT status FROM outbox_events").fetchall() == [("PROCESSED",)]
    templates = await search_client.indices.get_index_template(name=template_name_for(1))
    assert len(templates["index_templates"]) == 1


def test_worker_exits_with_error_code_when_password_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Şifre tanımlı değilse işçi hata koduyla çıkar."""
    monkeypatch.delenv("DB_PASSWORD", raising=False)

    with pytest.raises(SystemExit) as exit_info:
        app.main()

    assert exit_info.value.code == 2


def test_log_lines_are_json() -> None:
    """Log satırları JSON biçimindedir."""
    record = logging.LogRecord("news_worker.test", logging.INFO, __file__, 1, "Besleme sayısı: %d", (42,), None)

    entry = json.loads(JsonFormatter().format(record))

    assert entry["message"] == "Besleme sayısı: 42"
    assert entry["log.level"] == "INFO"
    assert entry["log.logger"] == "news_worker.test"
    assert entry["service.name"] == "news-worker"
    assert "@timestamp" in entry


def test_http_client_request_lines_are_not_logged() -> None:
    """httpx'in ve Elasticsearch istemcisinin her istek için yazdığı satırlar loga girmez."""
    root = logging.getLogger()
    handlers, level = root.handlers, root.level
    try:
        configure_logging()

        assert logging.getLogger("httpx").isEnabledFor(logging.INFO) is False
        assert logging.getLogger("httpx").isEnabledFor(logging.WARNING) is True
        assert logging.getLogger("elastic_transport.transport").isEnabledFor(logging.WARNING) is False
        assert logging.getLogger("elastic_transport.transport").isEnabledFor(logging.ERROR) is True
        assert logging.getLogger("news_worker").isEnabledFor(logging.INFO) is True
    finally:
        # Diğer testlerin log ayarı bozulmasın.
        root.handlers, root.level = handlers, level
        logging.getLogger("httpx").setLevel(logging.NOTSET)
        logging.getLogger("elastic_transport").setLevel(logging.NOTSET)
