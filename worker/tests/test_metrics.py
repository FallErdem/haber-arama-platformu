"""İşçinin ölçümlerinin testleri (FOG-40)."""

import psycopg
from conftest import metric_value

from news_worker.database import Database
from news_worker.feeds import FeedFailureCount, FeedRepository
from news_worker.metrics import FeedFailureMetricsUpdater, FetchResult, WorkerMetrics

FETCHES = "news_worker_feed_fetches_total"
FAILURES = "news_worker_feed_consecutive_failures"


def test_fetch_results_are_counted_per_source_and_result() -> None:
    """Okuma sonuçları kaynağa ve sonuca göre ayrı ayrı sayılır."""
    metrics = WorkerMetrics()

    metrics.record_fetch("TRT", FetchResult.SUCCEEDED)
    metrics.record_fetch("TRT", FetchResult.SUCCEEDED)
    metrics.record_fetch("TRT", FetchResult.FAILED)
    metrics.record_fetch("NTV", FetchResult.NOT_MODIFIED)

    assert metric_value(metrics, FETCHES, source="TRT", result="succeeded") == 2
    assert metric_value(metrics, FETCHES, source="TRT", result="failed") == 1
    assert metric_value(metrics, FETCHES, source="NTV", result="not_modified") == 1


def test_new_failure_counts_replace_the_old_ones() -> None:
    """Hata sayıları her seferinde baştan yazılır: listede artık olmayan besleme ölçümden de çıkar."""
    metrics = WorkerMetrics()
    metrics.set_feed_failures(
        [FeedFailureCount("TRT", "https://trt.test/a", 2), FeedFailureCount("TRT", "https://trt.test/b", 0)]
    )

    metrics.set_feed_failures([FeedFailureCount("TRT", "https://trt.test/b", 1)])

    assert metric_value(metrics, FAILURES, source="TRT", feed="https://trt.test/a") is None
    assert metric_value(metrics, FAILURES, source="TRT", feed="https://trt.test/b") == 1


def feed_urls(admin: psycopg.Connection, source_code: str, count: int) -> list[str]:
    rows = admin.execute(
        "SELECT f.url FROM feeds f JOIN sources s ON s.id = f.source_id WHERE s.code = %s ORDER BY f.url LIMIT %s",
        (source_code, count),
    ).fetchall()
    return [row[0] for row in rows]


async def test_failure_counts_are_read_from_the_database(database: Database, admin: psycopg.Connection) -> None:
    """Hata sayıları veritabanından okunur. Kendiliğinden kapanan besleme kalır, elle kapatılan ve
    kaynağı kapalı olan besleme ölçüme girmez."""
    failing, auto_disabled, manually_disabled, healthy = feed_urls(admin, "TRT", 4)
    (closed_source_feed,) = feed_urls(admin, "GLOBALVOICES", 1)
    admin.execute("UPDATE feeds SET consecutive_failures = 3 WHERE url = %s", (failing,))
    admin.execute(
        "UPDATE feeds SET consecutive_failures = 5, enabled = false, disabled_reason = 'AUTO' WHERE url = %s",
        (auto_disabled,),
    )
    admin.execute(
        "UPDATE feeds SET consecutive_failures = 2, enabled = false, disabled_reason = 'MANUAL' WHERE url = %s",
        (manually_disabled,),
    )
    admin.execute("UPDATE feeds SET consecutive_failures = 4 WHERE url = %s", (closed_source_feed,))
    admin.execute("UPDATE sources SET enabled = false WHERE code = 'GLOBALVOICES'")
    metrics = WorkerMetrics()

    await FeedFailureMetricsUpdater(database, FeedRepository(), metrics, interval_seconds=30).update_once()

    assert metric_value(metrics, FAILURES, source="TRT", feed=failing) == 3
    assert metric_value(metrics, FAILURES, source="TRT", feed=auto_disabled) == 5
    assert metric_value(metrics, FAILURES, source="TRT", feed=healthy) == 0
    assert metric_value(metrics, FAILURES, source="TRT", feed=manually_disabled) is None
    assert metric_value(metrics, FAILURES, source="GLOBALVOICES", feed=closed_source_feed) is None
