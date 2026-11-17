"""Görsel indirme döngüsünün testleri: gerçek PostgreSQL ve gerçek MinIO; görsel siteleri `respx` ile taklit edilir."""

import asyncio
import logging
from typing import TYPE_CHECKING
from uuid import UUID

import httpx
import psycopg
import pytest
import respx
from conftest import MEDIA_BUCKET, make_image
from test_media import add_article

from news_worker.database import Database
from news_worker.feed_fetcher import create_http_client
from news_worker.image_downloader import ImageDownloader
from news_worker.media import MediaRepository
from news_worker.media_downloader import MAX_ATTEMPTS, MediaDownloader, retry_delay_minutes
from news_worker.object_storage import ObjectStorage, create_storage_client
from news_worker.rate_limiter import SourceRateLimiter

if TYPE_CHECKING:
    from types_boto3_s3 import S3Client


class RecordingSleep:
    """İstek sınırlayıcısının beklemelerini kaydeder; testler gerçekten beklemez."""

    def __init__(self) -> None:
        self.waits: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.waits.append(seconds)


def build_downloader(
    database: Database, storage: ObjectStorage, sleep: RecordingSleep | None = None, batch_size: int = 50
) -> MediaDownloader:
    return MediaDownloader(
        database,
        MediaRepository(),
        ImageDownloader(create_http_client("HaberAramaPlatformu/test", 5), total_timeout_seconds=5),
        storage,
        SourceRateLimiter(sleep=sleep or RecordingSleep()),
        interval_seconds=60,
        batch_size=batch_size,
    )


def media_rows(admin: psycopg.Connection) -> list[tuple[object, ...]]:
    return admin.execute(
        "SELECT source_url, status, attempts, content_type, width, height, size_bytes IS NOT NULL, "
        "storage_key = 'articles/' || article_id || '/' || id FROM media ORDER BY source_url"
    ).fetchall()


async def test_image_is_downloaded_stored_and_recorded(
    database: Database,
    admin: psycopg.Connection,
    trt_feed: tuple[UUID, UUID],
    storage: ObjectStorage,
    storage_client: S3Client,
    respx_mock: respx.MockRouter,
) -> None:
    """Bekleyen görsel indirilir, MinIO'ya yüklenir ve satırı türü ile ölçüleriyle güncellenir."""
    await add_article(database, trt_feed, images=1)
    body = make_image("WEBP", size=(120, 80))
    respx_mock.get("https://images.example.test/1-0.jpg").respond(200, content=body)

    count = await build_downloader(database, storage).download_batch()

    assert count == 1
    assert media_rows(admin) == [
        ("https://images.example.test/1-0.jpg", "DOWNLOADED", 1, "image/webp", 120, 80, True, True)
    ]
    key = admin.execute("SELECT storage_key FROM media").fetchone()
    assert key is not None
    stored = storage_client.get_object(Bucket=MEDIA_BUCKET, Key=key[0])
    assert stored["Body"].read() == body
    assert stored["ContentType"] == "image/webp"


async def test_missing_image_fails_at_once(
    database: Database,
    admin: psycopg.Connection,
    trt_feed: tuple[UUID, UUID],
    storage: ObjectStorage,
    respx_mock: respx.MockRouter,
) -> None:
    """Kaynakta olmayan görsel (404) bir daha denenmez; haberde yer tutucu gösterilir."""
    await add_article(database, trt_feed, images=1)
    respx_mock.get("https://images.example.test/1-0.jpg").respond(404)

    await build_downloader(database, storage).download_batch()

    assert admin.execute("SELECT status, attempts, last_error FROM media").fetchall() == [("FAILED", 1, "HTTP 404")]


async def test_temporary_failure_is_retried_and_fails_after_last_attempt(
    database: Database,
    admin: psycopg.Connection,
    trt_feed: tuple[UUID, UUID],
    storage: ObjectStorage,
    respx_mock: respx.MockRouter,
) -> None:
    """Geçici hatada görsel 1, 5, 15 ve 15 dakika sonra yeniden denenir; 5. hatada FAILED olur."""
    await add_article(database, trt_feed, images=1)
    respx_mock.get("https://images.example.test/1-0.jpg").respond(503)
    downloader = build_downloader(database, storage)

    delays = []
    for _ in range(MAX_ATTEMPTS - 1):
        await downloader.download_batch()
        row = admin.execute(
            "SELECT status, round(extract(epoch FROM next_attempt_at - now()) / 60) FROM media"
        ).fetchone()
        assert row is not None
        assert row[0] == "PENDING"
        delays.append(int(row[1]))
        # Bir sonraki denemenin zamanı gelmiş gibi.
        admin.execute("UPDATE media SET next_attempt_at = now()")
    await downloader.download_batch()

    assert delays == [1, 5, 15, 15]
    assert admin.execute("SELECT status, attempts FROM media").fetchall() == [("FAILED", MAX_ATTEMPTS)]


@pytest.mark.parametrize(("attempts", "minutes"), [(0, 1), (1, 5), (2, 15), (3, 15)])
def test_retry_delay(attempts: int, minutes: int) -> None:
    """Önceki başarısız deneme sayısına göre bekleme süresi."""
    assert retry_delay_minutes(attempts) == minutes


async def test_page_instead_of_image_fails_at_once(
    database: Database,
    admin: psycopg.Connection,
    trt_feed: tuple[UUID, UUID],
    storage: ObjectStorage,
    respx_mock: respx.MockRouter,
) -> None:
    """Adres görsel yerine sayfa döndürürse görsel FAILED olur ve depolamaya hiçbir şey yazılmaz."""
    await add_article(database, trt_feed, images=1)
    respx_mock.get("https://images.example.test/1-0.jpg").respond(200, content=b"<html>Haber</html>")

    await build_downloader(database, storage).download_batch()

    row = admin.execute("SELECT status, storage_key, last_error FROM media").fetchone()
    assert row is not None
    assert row[:2] == ("FAILED", None)
    assert "Görsel olarak açılamadı" in row[2]


async def test_images_of_one_source_respect_its_request_interval(
    database: Database,
    admin: psycopg.Connection,
    trt_feed: tuple[UUID, UUID],
    storage: ObjectStorage,
    respx_mock: respx.MockRouter,
) -> None:
    """Aynı kaynağın görselleri arasında kaynağın istek aralığı kadar beklenir (TRT: 5 sn; FG-VT-14)."""
    await add_article(database, trt_feed, images=3)
    respx_mock.route(host="images.example.test").respond(200, content=make_image())
    sleep = RecordingSleep()

    await build_downloader(database, storage, sleep=sleep).download_batch()

    assert [status for (_, status, *_) in media_rows(admin)] == ["DOWNLOADED"] * 3
    # İlk istekten önce beklenmez; sonraki ikisinden önce yaklaşık 5 saniye beklenir.
    assert len(sleep.waits) == 2
    assert all(4 < wait <= 5 for wait in sleep.waits)


async def test_feed_reads_and_image_downloads_share_the_same_limiter(
    database: Database,
    admin: psycopg.Connection,
    trt_feed: tuple[UUID, UUID],
    storage: ObjectStorage,
    respx_mock: respx.MockRouter,
) -> None:
    """Besleme okuması ve görsel indirmesi aynı sınırlayıcıyı kullanırsa ikisi arasında da beklenir."""
    await add_article(database, trt_feed, images=1)
    respx_mock.route(host="images.example.test").respond(200, content=make_image())
    sleep = RecordingSleep()
    limiter = SourceRateLimiter(sleep=sleep)
    downloader = MediaDownloader(
        database,
        MediaRepository(),
        ImageDownloader(create_http_client("t", 5), total_timeout_seconds=5),
        storage,
        limiter,
        interval_seconds=60,
        batch_size=50,
    )
    # Az önce TRT'ye bir besleme isteği atılmış gibi.
    async with limiter.request_slot("TRT", 5):
        pass

    await downloader.download_batch()

    assert len(sleep.waits) == 1


async def test_storage_outage_leaves_images_untouched(
    database: Database,
    admin: psycopg.Connection,
    trt_feed: tuple[UUID, UUID],
    respx_mock: respx.MockRouter,
) -> None:
    """MinIO'ya ulaşılamazsa görselin deneme hakkı harcanmaz; bir sonraki turda yeniden denenir."""
    await add_article(database, trt_feed, images=1)
    respx_mock.get("https://images.example.test/1-0.jpg").respond(200, content=make_image())
    unreachable = ObjectStorage(create_storage_client("http://127.0.0.1:9", "x", "x", timeout_seconds=1), MEDIA_BUCKET)
    stop = asyncio.Event()
    downloader = MediaDownloader(
        database,
        MediaRepository(),
        ImageDownloader(create_http_client("t", 5), total_timeout_seconds=5),
        unreachable,
        SourceRateLimiter(sleep=RecordingSleep()),
        interval_seconds=0.05,
        batch_size=50,
    )

    task = asyncio.create_task(downloader.run(stop))
    await asyncio.sleep(1)
    stop.set()
    await asyncio.wait_for(task, timeout=10)

    assert admin.execute("SELECT status, attempts, last_error FROM media").fetchall() == [("PENDING", 0, None)]


async def test_storage_outage_is_logged_without_stack_trace(
    database: Database,
    admin: psycopg.Connection,
    trt_feed: tuple[UUID, UUID],
    respx_mock: respx.MockRouter,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Depolama kesintisi beklenen bir durumdur; loga tek satır uyarı düşer."""
    await add_article(database, trt_feed, images=1)
    respx_mock.get("https://images.example.test/1-0.jpg").respond(200, content=make_image())
    unreachable = ObjectStorage(create_storage_client("http://127.0.0.1:9", "x", "x", timeout_seconds=1), MEDIA_BUCKET)
    stop = asyncio.Event()
    downloader = MediaDownloader(
        database,
        MediaRepository(),
        ImageDownloader(create_http_client("t", 5), total_timeout_seconds=5),
        unreachable,
        SourceRateLimiter(sleep=RecordingSleep()),
        interval_seconds=0.05,
        batch_size=50,
    )

    with caplog.at_level(logging.WARNING, logger="news_worker.media_downloader"):
        task = asyncio.create_task(downloader.run(stop))
        await asyncio.sleep(1)
        stop.set()
        await asyncio.wait_for(task, timeout=10)

    warnings = [record for record in caplog.records if "Nesne depolamaya ulaşılamadı" in record.getMessage()]
    assert warnings
    assert all(record.exc_info is None for record in warnings)


async def test_sources_are_downloaded_in_parallel(
    database: Database,
    admin: psycopg.Connection,
    trt_feed: tuple[UUID, UUID],
    storage: ObjectStorage,
    respx_mock: respx.MockRouter,
) -> None:
    """Farklı kaynakların görselleri birbirini beklemez: biri yavaşken diğeri tamamlanır."""
    row = admin.execute(
        "SELECT s.id, f.id FROM feeds f JOIN sources s ON s.id = f.source_id WHERE s.code = 'NTV' LIMIT 1"
    ).fetchone()
    assert row is not None
    await add_article(database, trt_feed, number=1, images=1)
    await add_article(database, (row[0], row[1]), number=2, images=1)
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow(request: httpx.Request) -> httpx.Response:
        started.set()
        await release.wait()
        return httpx.Response(200, content=make_image())

    respx_mock.get("https://images.example.test/1-0.jpg").mock(side_effect=slow)
    respx_mock.get("https://images.example.test/2-0.jpg").respond(200, content=make_image())

    task = asyncio.create_task(build_downloader(database, storage).download_batch())
    await asyncio.wait_for(started.wait(), timeout=5)
    # TRT'nin görseli hâlâ indiriliyor; NTV'ninki o sırada biter.
    statuses: dict[str, str] = {}
    for _ in range(100):
        statuses = dict(admin.execute("SELECT source_url, status FROM media").fetchall())
        if statuses["https://images.example.test/2-0.jpg"] == "DOWNLOADED":
            break
        await asyncio.sleep(0.05)
    assert statuses == {
        "https://images.example.test/1-0.jpg": "PENDING",
        "https://images.example.test/2-0.jpg": "DOWNLOADED",
    }
    release.set()
    await asyncio.wait_for(task, timeout=5)


async def test_loop_continues_without_waiting_while_batches_are_full(
    database: Database,
    admin: psycopg.Connection,
    trt_feed: tuple[UUID, UUID],
    storage: ObjectStorage,
    respx_mock: respx.MockRouter,
) -> None:
    """Grup dolu geldikçe döngü beklemez: 5 görsel, 2'şerli gruplarla, 60 saniyelik aralık beklenmeden biter."""
    await add_article(database, trt_feed, images=5)
    respx_mock.route(host="images.example.test").respond(200, content=make_image())
    stop = asyncio.Event()

    task = asyncio.create_task(build_downloader(database, storage, batch_size=2).run(stop))
    for _ in range(200):
        if admin.execute("SELECT count(*) FROM media WHERE status = 'PENDING'").fetchone() == (0,):
            break
        await asyncio.sleep(0.05)
    stop.set()
    await asyncio.wait_for(task, timeout=5)

    assert [status for (_, status, *_) in media_rows(admin)] == ["DOWNLOADED"] * 5


async def test_each_round_is_summarized_in_one_log_line(
    database: Database,
    admin: psycopg.Connection,
    trt_feed: tuple[UUID, UUID],
    storage: ObjectStorage,
    respx_mock: respx.MockRouter,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Her turun sonucu tek satırda loglanır: kaç görsel indi, kaçı yeniden denenecek, kaçı başarısız."""
    await add_article(database, trt_feed, images=3)
    respx_mock.get("https://images.example.test/1-0.jpg").respond(200, content=make_image())
    respx_mock.get("https://images.example.test/1-1.jpg").respond(503)
    respx_mock.get("https://images.example.test/1-2.jpg").respond(404)
    downloader = build_downloader(database, storage)

    with caplog.at_level(logging.INFO, logger="news_worker.media_downloader"):
        await downloader.download_batch()
        # İkinci turda bekleyen görsel yok (yeniden denenecek olanın zamanı gelmedi); satır yazılmaz.
        await downloader.download_batch()

    summaries = [record.getMessage() for record in caplog.records if record.getMessage().startswith("Görseller")]
    assert summaries == ["Görseller işlendi (indirilen: 1, yeniden denenecek: 1, başarısız: 1)"]
