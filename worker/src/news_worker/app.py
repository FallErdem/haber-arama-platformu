"""İşçinin parçalarını birbirine bağlar ve çalıştırır."""

import asyncio
import logging
import signal

from news_worker.articles import ArticleRepository
from news_worker.audit import AuditRepository
from news_worker.config import ConfigurationError, Settings
from news_worker.database import Database
from news_worker.feed_fetcher import FeedFetcher, create_http_client
from news_worker.feed_reader import FeedReader
from news_worker.feeds import FeedRepository
from news_worker.health import HealthServer
from news_worker.image_downloader import ImageDownloader
from news_worker.ingestion_service import IngestionService
from news_worker.logging_config import configure_logging
from news_worker.maintenance import Maintenance, MaintenanceRepository, RetentionPeriods
from news_worker.media import MediaRepository
from news_worker.media_downloader import MediaDownloader
from news_worker.metrics import FeedFailureMetricsUpdater, WorkerMetrics
from news_worker.object_storage import ObjectStorage, create_storage_client
from news_worker.outbox import OutboxRepository
from news_worker.outbox_relay import OutboxRelay
from news_worker.rate_limiter import SourceRateLimiter
from news_worker.scheduler import Scheduler
from news_worker.search_index import SearchIndex, create_search_client
from news_worker.source_purge import SourcePurger, SourcePurgeRepository

log = logging.getLogger(__name__)


async def run(settings: Settings, stop: asyncio.Event) -> None:
    """Sağlık adresini açar, tabloları bekler ve durdurma istenene kadar işleri çalıştırır.

    Altı iş yan yana çalışır: zamanlayıcı (haber toplama), outbox aktarımı (Elasticsearch), görsel
    indirme (MinIO), kaynak içeriğinin silinmesi, bakım (yaşam döngüsü durumu, eski kayıtların temizliği)
    ve besleme hata sayılarının ölçüme yazılması (Prometheus).
    """
    database = Database(settings)
    # Ölçümler tek yerde toplanır: toplama servisi sayaçları artırır, sağlık sunucusu /metrics'te yayımlar.
    metrics = WorkerMetrics()
    # Bütün indirmeler tek bir HTTP istemcisini paylaşır; blok bitince istemci ve açık bağlantıları kapanır.
    # Elasticsearch istemcisi de aynı şekilde blok bitince kapanır.
    async with (
        create_http_client(settings.http_user_agent, settings.http_timeout_seconds) as http_client,
        create_search_client(
            settings.es_url, settings.es_user, settings.es_password, settings.es_timeout_seconds
        ) as search_client,
    ):
        # Tek sınırlayıcı: bir kaynağa giden bütün istekler (besleme ve görsel) aynı sırayı ve aynı
        # bekleme süresini paylaşır.
        rate_limiter = SourceRateLimiter()
        ingestion_service = IngestionService(
            database,
            FeedFetcher(http_client, settings.http_total_timeout_seconds),
            FeedReader(),
            rate_limiter,
            metrics,
        )
        scheduler = Scheduler(database, FeedRepository(), ingestion_service.ingest, settings.scheduler_interval_seconds)
        outbox_relay = OutboxRelay(
            database,
            OutboxRepository(),
            ArticleRepository(),
            search_client,
            SearchIndex(search_client),
            settings.outbox_interval_seconds,
            settings.outbox_batch_size,
        )
        # Görsel indirme ve içerik silme aynı MinIO istemcisini paylaşır.
        storage = ObjectStorage(
            create_storage_client(
                settings.minio_url,
                settings.minio_access_key,
                settings.minio_secret_key,
                settings.http_timeout_seconds,
            ),
            settings.media_bucket,
        )
        media_downloader = MediaDownloader(
            database,
            MediaRepository(),
            ImageDownloader(http_client, settings.http_total_timeout_seconds),
            storage,
            rate_limiter,
            settings.media_interval_seconds,
            settings.media_batch_size,
        )
        source_purger = SourcePurger(
            database,
            SourcePurgeRepository(),
            AuditRepository(),
            storage,
            settings.purge_interval_seconds,
            settings.purge_batch_size,
        )
        maintenance = Maintenance(
            database,
            MaintenanceRepository(),
            RetentionPeriods(
                outbox_days=settings.outbox_retention_days,
                ingestion_run_days=settings.ingestion_run_retention_days,
                feed_test_days=settings.feed_test_retention_days,
            ),
            settings.maintenance_interval_seconds,
        )
        feed_failure_metrics = FeedFailureMetricsUpdater(
            database, FeedRepository(), metrics, settings.metrics_interval_seconds
        )
        # Hazır olma yalnızca zamanlayıcıya bakar: Elasticsearch veya MinIO kapalıyken de haber toplama
        # sürer; notlar ve görseller PostgreSQL'de bekler (FOG-09). İşçi bu yüzden sağlıksız sayılmaz.
        health_server = HealthServer(settings.health_port, is_ready=scheduler.is_healthy, metrics=metrics)

        # Sağlık adresi beklemeden önce açılır: tablolar beklenirken işçi "ayakta ama
        # hazır değil" görünür ve Kubernetes onu yeniden başlatmaz.
        await health_server.start()
        try:
            log.info("İşçi başladı; tabloların hazır olması bekleniyor")
            await database.wait_until_ready(stop)
            if not stop.is_set():
                log.info("Tablolar hazır; zamanlayıcı başlıyor")
                # gather: döngüler aynı anda çalışır; durdurma istenince hepsi elindeki işi bitirip döner.
                await asyncio.gather(
                    scheduler.run(stop),
                    outbox_relay.run(stop),
                    media_downloader.run(stop),
                    source_purger.run(stop),
                    maintenance.run(stop),
                    feed_failure_metrics.run(stop),
                )
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
