import asyncio
from collections import Counter

import psycopg
from conftest import count_enabled_feeds
from psycopg.rows import TupleRow

from news_worker.database import Database
from news_worker.feeds import DueFeed, FeedRepository
from news_worker.scheduler import Scheduler


class FailingFeedRepository(FeedRepository):
    """Her çağrıda hata veren sahte repository; kaç kez çağrıldığını sayar."""

    def __init__(self) -> None:
        self.calls = 0

    async def find_due(self, connection: psycopg.AsyncConnection[TupleRow], limit: int) -> list[DueFeed]:
        self.calls += 1
        raise RuntimeError("deneme hatası")


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class RecordingIngest:
    """Toplama servisinin yerine geçer: gerçek siteye gidilmez, hangi beslemelerin istendiği kaydedilir."""

    def __init__(self) -> None:
        self.feeds: list[DueFeed] = []

    async def __call__(self, feed: DueFeed) -> None:
        self.feeds.append(feed)


async def run_briefly(scheduler: Scheduler, seconds: float) -> None:
    """Zamanlayıcıyı kısa bir süre çalıştırır, sonra gerçekte olduğu gibi durdurma isteyip bitmesini bekler."""
    stop = asyncio.Event()
    task = asyncio.create_task(scheduler.run(stop))
    await asyncio.sleep(seconds)
    stop.set()
    async with asyncio.timeout(5):
        await task


async def test_tick_ingests_every_due_feed(database: Database, admin: psycopg.Connection) -> None:
    """Bir tur, okuma zamanı gelmiş her beslemeyi bir kez toplatır."""
    enabled_feed_count = count_enabled_feeds(admin)
    ingest = RecordingIngest()
    scheduler = Scheduler(database, FeedRepository(), ingest, interval_seconds=30, batch_size=enabled_feed_count + 1)

    assert await scheduler.tick() == enabled_feed_count

    assert len(ingest.feeds) == enabled_feed_count
    assert len({feed.id for feed in ingest.feeds}) == enabled_feed_count


async def test_feeds_of_a_source_run_in_order_while_sources_run_together(database: Database) -> None:
    """Aynı kaynağın beslemeleri sırayla, farklı kaynaklar aynı anda okunur (ADR-0013)."""
    running: Counter[str] = Counter()
    max_running_per_source: Counter[str] = Counter()
    max_running_in_total = 0

    async def ingest(feed: DueFeed) -> None:
        nonlocal max_running_in_total
        running[feed.source_code] += 1
        max_running_per_source[feed.source_code] = max(
            max_running_per_source[feed.source_code], running[feed.source_code]
        )
        max_running_in_total = max(max_running_in_total, sum(running.values()))
        # Diğer görevlere çalışma fırsatı verilir; aynı anda sürenler bu sırada görünür olur.
        await asyncio.sleep(0.01)
        running[feed.source_code] -= 1

    scheduler = Scheduler(database, FeedRepository(), ingest, interval_seconds=30)

    await scheduler.tick()

    assert set(max_running_per_source) == {"TRT", "NTV", "CNNTURK", "GLOBALVOICES"}
    assert set(max_running_per_source.values()) == {1}
    assert max_running_in_total == 4


async def test_failing_feed_does_not_stop_other_feeds(database: Database, admin: psycopg.Connection) -> None:
    """Bir beslemenin hatası ne kendi kaynağının diğer beslemelerini ne de başka kaynakları durdurur (FOG-08)."""
    enabled_feed_count = count_enabled_feeds(admin)
    attempted: list[DueFeed] = []

    async def ingest(feed: DueFeed) -> None:
        attempted.append(feed)
        if feed.source_code == "TRT":
            raise RuntimeError("deneme hatası")

    scheduler = Scheduler(database, FeedRepository(), ingest, interval_seconds=30)

    await scheduler.tick()

    assert len(attempted) == enabled_feed_count


async def test_remaining_feeds_are_not_started_after_stop_is_requested(database: Database) -> None:
    """Durdurma istenince elindeki beslemeyi bitirir; kaynağın sıradaki beslemelerine başlamaz."""
    stop = asyncio.Event()
    ingest = RecordingIngest()

    async def ingest_and_request_stop(feed: DueFeed) -> None:
        await ingest(feed)
        # Diğer kaynakların görevlerine başlama fırsatı verilir; durdurma ancak ondan sonra istenir.
        await asyncio.sleep(0.01)
        stop.set()

    scheduler = Scheduler(database, FeedRepository(), ingest_and_request_stop, interval_seconds=30)

    await scheduler.tick(stop)

    # Dört kaynağın ilk beslemeleri aynı anda başlamıştı; hiçbir kaynağın ikinci beslemesi başlamadı.
    assert Counter(feed.source_code for feed in ingest.feeds) == Counter(
        {"TRT": 1, "NTV": 1, "CNNTURK": 1, "GLOBALVOICES": 1}
    )


async def test_not_healthy_before_first_tick(database: Database) -> None:
    """İlk turdan önce sağlıklı sayılmaz."""
    scheduler = Scheduler(database, FeedRepository(), RecordingIngest(), interval_seconds=30)

    assert scheduler.is_healthy() is False


async def test_healthy_after_tick(database: Database) -> None:
    """Turdan sonra sağlıklı sayılır."""
    scheduler = Scheduler(database, FeedRepository(), RecordingIngest(), interval_seconds=30)

    await scheduler.tick()

    assert scheduler.is_healthy() is True


async def test_not_healthy_when_last_activity_is_too_old(database: Database) -> None:
    """Son canlılık işareti üç aralıktan eskiyse sağlıklı sayılmaz."""
    clock = FakeClock()
    scheduler = Scheduler(database, FeedRepository(), RecordingIngest(), interval_seconds=30, clock=clock)
    await scheduler.tick()

    clock.now += 30 * 3
    assert scheduler.is_healthy() is True

    clock.now += 1
    assert scheduler.is_healthy() is False


async def test_stays_healthy_during_a_long_tick(database: Database) -> None:
    """Tur eşikten uzun sürse de, her beslemeden sonra canlılık işareti yenilendiği için sağlıklı kalır."""
    clock = FakeClock()
    health_during_tick: list[bool] = []
    scheduler: Scheduler

    async def slow_ingest(feed: DueFeed) -> None:
        # Her besleme 40 saniye sürer; toplam süre 90 saniyelik eşiği kat kat aşar.
        clock.now += 40
        health_during_tick.append(scheduler.is_healthy())

    scheduler = Scheduler(database, FeedRepository(), slow_ingest, interval_seconds=30, clock=clock)

    await scheduler.tick()

    assert len(health_during_tick) > 3
    assert all(health_during_tick)
    assert scheduler.is_healthy() is True


async def test_loop_repeats_ticks_until_stop_is_requested(database: Database) -> None:
    """Döngü, durdurma istenene kadar turları tekrarlar ve sonra düzgünce biter."""
    ingest = RecordingIngest()
    scheduler = Scheduler(database, FeedRepository(), ingest, interval_seconds=0.05)

    await run_briefly(scheduler, seconds=0.5)

    assert scheduler.is_healthy() is True
    # Sahte toplama beslemeleri ileri atmadığı için her turda yeniden bulunurlar: birden fazla tur dönmüştür.
    assert len(ingest.feeds) > len({feed.id for feed in ingest.feeds})


async def test_failing_tick_does_not_stop_the_loop(database: Database) -> None:
    """Bir turdaki hata döngüyü durdurmaz."""
    repository = FailingFeedRepository()
    scheduler = Scheduler(database, repository, RecordingIngest(), interval_seconds=0.05)

    await run_briefly(scheduler, seconds=0.5)

    # Hata döngüyü öldürseydi repository yalnızca bir kez çağrılırdı.
    assert repository.calls >= 2
    assert scheduler.is_healthy() is False
