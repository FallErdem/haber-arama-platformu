import asyncio

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


async def run_briefly(scheduler: Scheduler, seconds: float) -> None:
    """Zamanlayıcıyı kısa bir süre çalıştırır, sonra gerçekte olduğu gibi durdurma isteyip bitmesini bekler."""
    stop = asyncio.Event()
    task = asyncio.create_task(scheduler.run(stop))
    await asyncio.sleep(seconds)
    stop.set()
    async with asyncio.timeout(5):
        await task


async def test_tick_counts_due_feeds(database: Database, admin: psycopg.Connection) -> None:
    """Bir tur, okuma zamanı gelmiş beslemeleri sayar."""
    enabled_feed_count = count_enabled_feeds(admin)
    scheduler = Scheduler(database, FeedRepository(), interval_seconds=30, batch_size=enabled_feed_count + 1)

    assert await scheduler.tick() == enabled_feed_count


async def test_not_healthy_before_first_successful_tick(database: Database) -> None:
    """İlk başarılı turdan önce sağlıklı sayılmaz."""
    scheduler = Scheduler(database, FeedRepository(), interval_seconds=30)

    assert scheduler.is_healthy() is False


async def test_healthy_after_successful_tick(database: Database) -> None:
    """Başarılı turdan sonra sağlıklı sayılır."""
    scheduler = Scheduler(database, FeedRepository(), interval_seconds=30)

    await scheduler.tick()

    assert scheduler.is_healthy() is True


async def test_not_healthy_when_last_successful_tick_is_too_old(database: Database) -> None:
    """Son başarılı tur üç aralıktan eskiyse sağlıklı sayılmaz."""
    clock = FakeClock()
    scheduler = Scheduler(database, FeedRepository(), interval_seconds=30, clock=clock)
    await scheduler.tick()

    clock.now += 30 * 3
    assert scheduler.is_healthy() is True

    clock.now += 1
    assert scheduler.is_healthy() is False


async def test_loop_repeats_ticks_until_stop_is_requested(database: Database) -> None:
    """Döngü, durdurma istenene kadar turları tekrarlar ve sonra düzgünce biter."""
    scheduler = Scheduler(database, FeedRepository(), interval_seconds=0.05)

    await run_briefly(scheduler, seconds=0.5)

    assert scheduler.is_healthy() is True


async def test_failing_tick_does_not_stop_the_loop(database: Database) -> None:
    """Bir turdaki hata döngüyü durdurmaz."""
    repository = FailingFeedRepository()
    scheduler = Scheduler(database, repository, interval_seconds=0.05)

    await run_briefly(scheduler, seconds=0.5)

    # Hata döngüyü öldürseydi repository yalnızca bir kez çağrılırdı.
    assert repository.calls >= 2
    assert scheduler.is_healthy() is False
