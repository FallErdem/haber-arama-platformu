import asyncio
import json
import logging
from dataclasses import replace

import pytest

from news_worker import app
from news_worker.config import Settings
from news_worker.logging_config import JsonFormatter


async def test_worker_finds_tables_runs_ticks_and_stops_on_request(
    settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    """İşçi tabloları bulur, turları çalıştırır ve durdurma istenince düzgünce kapanır."""
    caplog.set_level(logging.INFO)
    stop = asyncio.Event()
    # 18080: testte sağlık adresi için sabit bir port; 8080 başka bir süreçte dolu olabilir.
    task = asyncio.create_task(app.run(replace(settings, health_port=18080), stop))

    await asyncio.sleep(0.5)
    stop.set()
    async with asyncio.timeout(5):
        await task

    messages = [record.getMessage() for record in caplog.records]
    assert "Tablolar hazır; zamanlayıcı başlıyor" in messages
    assert any(message.startswith("Okuma zamanı gelmiş besleme sayısı: ") for message in messages)
    assert messages[-1] == "İşçi durdu"


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
