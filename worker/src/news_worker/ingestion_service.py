"""Toplama akışı: bir beslemeyi indirir, okur, haberlerini kaydeder ve sonucu yazar (ADR-0013).

Parçaların her biri tek bir iş yapar (indirme, okuma, kategori bulma, kaydetme); burası onları
sıraya koyar ve sonuca göre ne yapılacağına karar verir: bir sonraki okuma zamanı, yeniden
deneme, erteleme veya beslemenin otomatik devre dışı bırakılması.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import psycopg
from psycopg.rows import TupleRow

from news_worker.articles import ArticleRepository, NewArticle
from news_worker.audit import AuditRepository
from news_worker.categories import CategoryRepository
from news_worker.category_resolver import CategoryResolver, FeedCategoryRule
from news_worker.database import Database
from news_worker.feed_fetcher import FailureKind, FeedFetcher, FeedNotModified, FetchedFeed
from news_worker.feed_reader import FeedParseError, FeedReader
from news_worker.feeds import DueFeed, FeedRepository
from news_worker.ingestion_runs import IngestionRunRepository, RunResult, RunStatus, RunTrigger
from news_worker.metrics import FetchResult, WorkerMetrics
from news_worker.parsed_article import ParsedArticle
from news_worker.rate_limiter import SourceRateLimiter

log = logging.getLogger(__name__)

# Art arda bu kadar başarısız okumadan sonra besleme otomatik olarak devre dışı kalır (FG-YP-07).
MAX_CONSECUTIVE_FAILURES = 5
# Başarısız okumadan sonra yeniden deneme süreleri: 1., 2. ve 3. hatadan sonra. Daha sonraki
# hatalarda son süre kullanılır (ADR-0013).
RETRY_DELAYS_MINUTES = (1, 5, 15)

FEED_AUTO_DISABLED_ACTION = "FEED_AUTO_DISABLED"
FEED_TARGET_TYPE = "FEED"


@dataclass(frozen=True)
class _SaveCounts:
    new: int
    duplicate: int
    failed: int


class IngestionService:
    def __init__(
        self,
        database: Database,
        fetcher: FeedFetcher,
        reader: FeedReader,
        rate_limiter: SourceRateLimiter,
        metrics: WorkerMetrics,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._database = database
        self._fetcher = fetcher
        self._reader = reader
        self._rate_limiter = rate_limiter
        # Okuma sonuçları sayılır. Sayaç, sonuç veritabanına yazıldıktan sonra artar; yazma hata verirse
        # okuma "başarısız" sayılır ve iki kez sayılmaz.
        self._metrics = metrics
        # Testlerde sabit bir zaman verilebilir.
        self._clock = clock
        self._feeds = FeedRepository()
        self._runs = IngestionRunRepository()
        self._articles = ArticleRepository()
        self._categories = CategoryRepository()
        self._audit = AuditRepository()

    async def ingest(self, feed: DueFeed) -> None:
        """Beslemeyi bir kez okur. Okumanın sonucu ne olursa olsun `ingestion_runs`'a yazılır."""
        async with await self._database.connect() as connection:
            # autocommit: tek başına çalışan her komut hemen kalıcı olur; birlikte kalıcı olması
            # gereken komutlar açıkça `connection.transaction()` bloğuna alınır. Böylece okumanın
            # "başladı" kaydı, indirme sürerken de veritabanında görünür.
            await connection.set_autocommit(True)
            # Yönetici bu besleme için elle toplama istediyse okuma MANUAL olarak kaydedilir (FG-YP-08).
            trigger = RunTrigger.SCHEDULED if feed.manual_fetch_requested_at is None else RunTrigger.MANUAL
            run_id = await self._runs.start(connection, feed.id, trigger)
            try:
                await self._collect(connection, feed, run_id)
            except Exception as error:
                # Öngörülmeyen bir hata da başarısız okumadır: kayıt RUNNING olarak kalmaz ve
                # besleme yeniden deneme kurallarına girer. Ayrıntı (yığın izi) loga yazılır.
                log.exception("Besleme toplanırken beklenmeyen hata: %s", feed.url)
                await self._fail(connection, feed, run_id, f"Beklenmeyen hata: {type(error).__name__}")

    async def _collect(self, connection: psycopg.AsyncConnection[TupleRow], feed: DueFeed, run_id: UUID) -> None:
        # Aynı kaynağa iki istek arasında kaynağın istek aralığı kadar beklenir (FG-VT-05).
        async with self._rate_limiter.request_slot(feed.source_code, feed.request_interval_seconds):
            fetched = await self._fetcher.fetch(feed.url, feed.etag, feed.last_modified)

        if isinstance(fetched, FeedNotModified):
            async with connection.transaction():
                await self._feeds.record_not_modified(connection, feed.id, feed.manual_fetch_requested_at)
                await self._runs.finish(
                    connection,
                    run_id,
                    RunResult(RunStatus.NOT_MODIFIED, http_status=fetched.http_status, final_url=fetched.final_url),
                )
            self._metrics.record_fetch(feed.source_code, FetchResult.NOT_MODIFIED)
            log.info("Besleme değişmemiş: %s", feed.url)
            return

        if not isinstance(fetched, FetchedFeed):
            if fetched.kind is FailureKind.RATE_LIMITED:
                # Besleme bozuk değil, kaynak daha seyrek gelinmesini istiyor: okuma ertelenir
                # ve hata sayacı artmaz.
                async with connection.transaction():
                    await self._feeds.record_postponed(
                        connection,
                        feed.id,
                        fetched.message,
                        fetched.retry_after_seconds,
                        feed.manual_fetch_requested_at,
                    )
                    await self._runs.finish(
                        connection,
                        run_id,
                        RunResult(
                            RunStatus.FAILED,
                            http_status=fetched.http_status,
                            final_url=fetched.final_url,
                            error_message=fetched.message,
                        ),
                    )
                self._metrics.record_fetch(feed.source_code, FetchResult.POSTPONED)
                log.warning("Besleme ertelendi: %s (%s)", feed.url, fetched.message)
                return
            # Erişim engeli (403) dahil diğer hatalar: aşılmaya çalışılmaz, başarısız okuma sayılır (FG-VT-06).
            await self._fail(connection, feed, run_id, fetched.message, fetched.http_status, fetched.final_url)
            return

        try:
            read = self._reader.read(fetched.body, feed.field_mapping, feed.feed_time_zone)
        except FeedParseError as error:
            await self._fail(connection, feed, run_id, str(error), fetched.http_status, fetched.final_url)
            return

        counts = await self._save_articles(connection, feed, read.articles)
        items_failed = read.skipped_count + counts.failed
        async with connection.transaction():
            await self._feeds.record_success(
                connection, feed.id, fetched.etag, fetched.last_modified, feed.manual_fetch_requested_at
            )
            await self._runs.finish(
                connection,
                run_id,
                RunResult(
                    RunStatus.SUCCEEDED,
                    http_status=fetched.http_status,
                    final_url=fetched.final_url,
                    items_received=len(read.articles) + read.skipped_count,
                    items_new=counts.new,
                    items_duplicate=counts.duplicate,
                    items_failed=items_failed,
                ),
            )
        self._metrics.record_fetch(feed.source_code, FetchResult.SUCCEEDED)
        log.info(
            "Besleme toplandı: %s (yeni: %d, tekrar: %d, atlanan: %d)",
            feed.url,
            counts.new,
            counts.duplicate,
            items_failed,
        )

    async def _save_articles(
        self,
        connection: psycopg.AsyncConnection[TupleRow],
        feed: DueFeed,
        articles: tuple[ParsedArticle, ...],
    ) -> _SaveCounts:
        """Haberleri tek tek kaydeder; her haber kendi işlemindedir."""
        resolver = CategoryResolver(await self._categories.find_topic_codes(connection))
        mappings = await self._categories.find_mappings(connection, feed.source_code)
        feed_rule = FeedCategoryRule(feed.default_category_code, feed.use_item_categories)
        fetched_at = self._clock()

        new = duplicate = failed = 0
        for article in articles:
            new_article = NewArticle(
                source_id=feed.source_id,
                feed_id=feed.id,
                language=feed.language,
                article=article,
                categories=resolver.resolve(article.source_categories, feed_rule, mappings),
                fetched_at=fetched_at,
            )
            try:
                inserted = await self._articles.insert_if_new(connection, new_article)
            except psycopg.DataError, psycopg.IntegrityError:
                # Verinin kendisinden kaynaklanan hata (örneğin saklanamayan bir karakter): yalnızca
                # bu haber atlanır, beslemenin diğer haberleri kaydedilir. Bağlantının kopması gibi
                # hatalar burada yakalanmaz; onlar okumanın tamamını başarısız yapar.
                log.exception("Haber kaydedilemedi: %s", article.url)
                failed += 1
                continue
            if inserted:
                new += 1
            else:
                duplicate += 1
        return _SaveCounts(new=new, duplicate=duplicate, failed=failed)

    async def _fail(
        self,
        connection: psycopg.AsyncConnection[TupleRow],
        feed: DueFeed,
        run_id: UUID,
        message: str,
        http_status: int | None = None,
        final_url: str | None = None,
    ) -> None:
        """Başarısız okumayı kaydeder: sayaç artar, yeniden deneme zamanı ayarlanır, gerekirse besleme kapatılır."""
        # Tek işlem: sayaç, beslemenin kapatılması, audit kaydı ve okuma kaydı birlikte yazılır;
        # "besleme kapandı ama audit kaydı yok" durumu oluşamaz (ADR-0016, 5. bölüm).
        async with connection.transaction():
            state = await self._feeds.lock_failure_state(connection, feed.id)
            consecutive_failures = state.consecutive_failures + 1
            # Elle kapatılmış bir besleme yeniden "otomatik kapatıldı" diye işaretlenmez.
            disable = state.enabled and consecutive_failures >= MAX_CONSECUTIVE_FAILURES
            retry_delay_minutes = RETRY_DELAYS_MINUTES[min(consecutive_failures, len(RETRY_DELAYS_MINUTES)) - 1]

            await self._feeds.record_failure(
                connection,
                feed.id,
                message,
                consecutive_failures,
                retry_delay_minutes,
                disable,
                feed.manual_fetch_requested_at,
            )
            if disable:
                await self._audit.insert_system_event(
                    connection,
                    FEED_AUTO_DISABLED_ACTION,
                    FEED_TARGET_TYPE,
                    feed.id,
                    {"consecutive_failures": consecutive_failures, "last_error": message},
                )
            await self._runs.finish(
                connection,
                run_id,
                RunResult(RunStatus.FAILED, http_status=http_status, final_url=final_url, error_message=message),
            )

        self._metrics.record_fetch(feed.source_code, FetchResult.FAILED)
        if disable:
            log.error("Besleme art arda %d kez okunamadı ve devre dışı bırakıldı: %s", consecutive_failures, feed.url)
        else:
            log.warning("Besleme okunamadı (%d. hata): %s (%s)", consecutive_failures, feed.url, message)
