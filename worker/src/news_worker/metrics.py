"""İşçinin ölçümleri (FOG-40). Prometheus bunları sağlık sunucusunun /metrics adresinden okur.

İki ölçüm vardır:
- Okuma sonuçları: her okuma bitince sonucunun sayacı bir artar (IngestionService).
- Beslemelerin art arda hata sayıları: belirli aralıklarla veritabanından okunur (FeedFailureMetricsUpdater).
  Gerçek sayı veritabanındadır; işçi yeniden başlasa da kaybolmaz. "Art arda başarısız kaynak"
  uyarısı bu ölçüme bakar (deploy/k8s/platform/prometheus/alerting-rules.yml).
"""

import asyncio
import logging
from collections.abc import Iterable
from enum import StrEnum

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, generate_latest

from news_worker.database import Database, wait_for_stop
from news_worker.feeds import FeedFailureCount, FeedRepository

log = logging.getLogger(__name__)


class FetchResult(StrEnum):
    SUCCEEDED = "succeeded"
    # İçerik değişmemiş (304).
    NOT_MODIFIED = "not_modified"
    FAILED = "failed"
    # Kaynak "çok sık geliyorsun" dedi (429); okuma ertelendi, hata sayılmadı.
    POSTPONED = "postponed"


class WorkerMetrics:
    # Prometheus'a yanıtın biçimini bildiren içerik türü.
    CONTENT_TYPE = CONTENT_TYPE_LATEST

    def __init__(self) -> None:
        # Kütüphanenin ortak kaydı yerine kendi kaydı: her testin ölçümleri ayrı kalır.
        self._registry = CollectorRegistry()
        # Kütüphane sayaç adının sonuna "_total" ekler: news_worker_feed_fetches_total.
        self._feed_fetches = Counter(
            "news_worker_feed_fetches",
            "Besleme okumaları, sonuca göre",
            ["source", "result"],
            registry=self._registry,
        )
        self._feed_failures = Gauge(
            "news_worker_feed_consecutive_failures",
            "Beslemenin art arda başarısız okuma sayısı",
            ["source", "feed"],
            registry=self._registry,
        )

    def record_fetch(self, source_code: str, result: FetchResult) -> None:
        self._feed_fetches.labels(source=source_code, result=result.value).inc()

    def set_feed_failures(self, counts: Iterable[FeedFailureCount]) -> None:
        # Önce hepsi silinir: silinen veya elle kapatılan besleme eski değeriyle listede kalmasın.
        self._feed_failures.clear()
        for count in counts:
            self._feed_failures.labels(source=count.source_code, feed=count.url).set(count.consecutive_failures)

    def render(self) -> bytes:
        """Ölçümlerin Prometheus'un okuduğu metin biçimi."""
        return generate_latest(self._registry)


class FeedFailureMetricsUpdater:
    """Beslemelerin art arda hata sayılarını belirli aralıklarla veritabanından okuyup ölçüme yazar."""

    def __init__(
        self,
        database: Database,
        repository: FeedRepository,
        metrics: WorkerMetrics,
        interval_seconds: float,
    ) -> None:
        self._database = database
        self._repository = repository
        self._metrics = metrics
        self._interval_seconds = interval_seconds

    async def update_once(self) -> None:
        async with await self._database.connect() as connection:
            counts = await self._repository.find_failure_counts(connection)
        self._metrics.set_feed_failures(counts)

    async def run(self, stop: asyncio.Event) -> None:
        """Durdurma istenene kadar ölçümü aralıklarla günceller."""
        while not stop.is_set():
            try:
                await self.update_once()
            except Exception:
                # Veritabanına ulaşılamazsa ölçüm son değerinde kalır; bir sonraki turda yeniden denenir.
                log.exception("Besleme hata sayıları okunamadı")
            await wait_for_stop(stop, self._interval_seconds)
