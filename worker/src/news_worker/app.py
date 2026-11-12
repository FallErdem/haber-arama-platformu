"""İşçinin parçalarını birbirine bağlar ve çalıştırır."""

import asyncio
import logging
import signal

from news_worker.config import ConfigurationError, Settings
from news_worker.database import Database
from news_worker.feeds import FeedRepository
from news_worker.health import HealthServer
from news_worker.logging_config import configure_logging
from news_worker.scheduler import Scheduler

log = logging.getLogger(__name__)


async def run(settings: Settings, stop: asyncio.Event) -> None:
    """Sağlık adresini açar, tabloları bekler ve durdurma istenene kadar zamanlayıcıyı çalıştırır."""
    database = Database(settings)
    scheduler = Scheduler(database, FeedRepository(), settings.scheduler_interval_seconds)
    health_server = HealthServer(settings.health_port, is_ready=scheduler.is_healthy)

    # Sağlık adresi beklemeden önce açılır: tablolar beklenirken işçi "ayakta ama
    # hazır değil" görünür ve Kubernetes onu yeniden başlatmaz.
    await health_server.start()
    try:
        log.info("İşçi başladı; tabloların hazır olması bekleniyor")
        await database.wait_until_ready(stop)
        if not stop.is_set():
            log.info("Tablolar hazır; zamanlayıcı başlıyor")
            await scheduler.run(stop)
    finally:
        await health_server.stop()
        log.info("İşçi durdu")


async def _run_until_signalled(settings: Settings) -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    # Kubernetes pod'u durdururken SIGTERM gönderir; elindeki tur bitince döngü düzgünce kapanır.
    for signal_number in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signal_number, stop.set)
    await run(settings, stop)


def main() -> None:
    configure_logging()
    try:
        settings = Settings.from_environment()
    except ConfigurationError as error:
        log.error("Yapılandırma hatası: %s", error)
        raise SystemExit(2) from None
    asyncio.run(_run_until_signalled(settings))
