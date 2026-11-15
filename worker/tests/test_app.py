import asyncio
import json
import logging
from dataclasses import replace

import psycopg
import pytest
import respx

from news_worker import app
from news_worker.config import Settings
from news_worker.logging_config import JsonFormatter, configure_logging


async def test_worker_finds_tables_ingests_due_feeds_and_stops_on_request(
    settings: Settings,
    admin: psycopg.Connection,
    respx_mock: respx.MockRouter,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """İşçi tabloları bulur, zamanı gelen beslemeleri toplar ve durdurma istenince düzgünce kapanır."""
    caplog.set_level(logging.INFO)
    # Gerçek sitelere gidilmez: her istek sahte bir "değişmedi" yanıtı alır.
    respx_mock.route().respond(304)
    # Yalnızca iki ayrı kaynağın birer beslemesinin zamanı gelmiş olsun; aynı kaynağa ikinci
    # istek atılmadığı için istek aralığı beklenmez ve test hızlı biter.
    admin.execute("UPDATE feeds SET next_fetch_at = now() + interval '1 hour'")
    admin.execute(
        "UPDATE feeds SET next_fetch_at = now() WHERE url IN "
        "('https://www.trthaber.com/gundem_articles.rss', 'https://globalvoices.org/feed/')"
    )
    stop = asyncio.Event()
    # 18080: testte sağlık adresi için sabit bir port; 8080 başka bir süreçte dolu olabilir.
    task = asyncio.create_task(app.run(replace(settings, health_port=18080), stop))

    await asyncio.sleep(0.5)
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
    assert respx_mock.calls.last.request.headers["User-Agent"] == settings.http_user_agent


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
    """httpx'in her istek için yazdığı satırlar (adresle birlikte) loga girmez; uyarıları girer."""
    root = logging.getLogger()
    handlers, level = root.handlers, root.level
    try:
        configure_logging()

        assert logging.getLogger("httpx").isEnabledFor(logging.INFO) is False
        assert logging.getLogger("httpx").isEnabledFor(logging.WARNING) is True
        assert logging.getLogger("news_worker").isEnabledFor(logging.INFO) is True
    finally:
        # Diğer testlerin log ayarı bozulmasın.
        root.handlers, root.level = handlers, level
        logging.getLogger("httpx").setLevel(logging.NOTSET)
