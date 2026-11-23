import asyncio
from collections.abc import AsyncIterator

import pytest

from news_worker.health import LIVE_PATH, METRICS_PATH, READY_PATH, HealthServer
from news_worker.metrics import FetchResult, WorkerMetrics


class Readiness:
    """Testin açıp kapatabildiği sahte hazır olma durumu."""

    def __init__(self) -> None:
        self.ready = False

    def __call__(self) -> bool:
        return self.ready


@pytest.fixture
def readiness() -> Readiness:
    return Readiness()


@pytest.fixture
def metrics() -> WorkerMetrics:
    return WorkerMetrics()


@pytest.fixture
async def server(readiness: Readiness, metrics: WorkerMetrics) -> AsyncIterator[HealthServer]:
    # 0 numaralı port: işletim sistemi boş bir port seçer; testler çakışmaz.
    health_server = HealthServer(port=0, is_ready=readiness, metrics=metrics, host="127.0.0.1")
    await health_server.start()
    yield health_server
    await health_server.stop()


async def request(server: HealthServer, path: str) -> tuple[int, str, str]:
    """Kubernetes'in yaptığı gibi düz bir HTTP GET isteği gönderir; durum kodunu, başlıkları ve gövdeyi döner."""
    reader, writer = await asyncio.open_connection("127.0.0.1", server.port)
    writer.write(f"GET {path} HTTP/1.1\r\nHost: localhost\r\nUser-Agent: kube-probe/1.36\r\n\r\n".encode())
    await writer.drain()
    async with asyncio.timeout(5):
        response = (await reader.read()).decode()
    writer.close()
    await writer.wait_closed()

    head, _, body = response.partition("\r\n\r\n")
    status_code = int(head.split()[1])
    return status_code, head, body


async def get(server: HealthServer, path: str) -> tuple[int, str]:
    """Durum kodu ve gövde."""
    status_code, _, body = await request(server, path)
    return status_code, body


async def test_liveness_always_returns_200(server: HealthServer) -> None:
    """Ayakta kontrolü her zaman 200 döner."""
    assert await get(server, LIVE_PATH) == (200, "ok")


async def test_readiness_returns_503_when_not_ready(server: HealthServer) -> None:
    """Hazır değilken hazır kontrolü 503 döner."""
    assert await get(server, READY_PATH) == (503, "not ready")


async def test_readiness_returns_200_when_ready(server: HealthServer, readiness: Readiness) -> None:
    """Hazır olunca hazır kontrolü 200 döner."""
    readiness.ready = True

    assert await get(server, READY_PATH) == (200, "ready")


async def test_metrics_are_served_in_prometheus_format(server: HealthServer, metrics: WorkerMetrics) -> None:
    """Ölçüm adresi, Prometheus'un tanıdığı içerik türüyle ölçümleri döner."""
    metrics.record_fetch("TRT", FetchResult.SUCCEEDED)

    status_code, head, body = await request(server, METRICS_PATH)

    assert status_code == 200
    assert f"Content-Type: {WorkerMetrics.CONTENT_TYPE}" in head.splitlines()
    assert 'news_worker_feed_fetches_total{result="succeeded",source="TRT"} 1.0' in body.splitlines()


async def test_unknown_path_returns_404(server: HealthServer) -> None:
    """Bilinmeyen adres 404 döner."""
    status_code, _ = await get(server, "/baska")

    assert status_code == 404


async def test_aborted_request_does_not_break_the_server(server: HealthServer) -> None:
    """Hiçbir şey göndermeden kapanan bir bağlantıdan sonra sunucu yanıt vermeye devam eder."""
    _, writer = await asyncio.open_connection("127.0.0.1", server.port)
    writer.close()
    await writer.wait_closed()

    assert await get(server, LIVE_PATH) == (200, "ok")
