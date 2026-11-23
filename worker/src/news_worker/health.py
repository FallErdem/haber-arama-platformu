"""Kubernetes'in sağlık kontrolleri (FOG-13) ve Prometheus'un ölçümleri (FOG-40) için küçük bir HTTP sunucusu.

Yalnızca üç adres sunar; bunun için bir web çatısı eklemek yerine Python'un
kendi asyncio araçları kullanılır.
"""

import asyncio
import contextlib
import logging
from collections.abc import Callable

from news_worker.metrics import WorkerMetrics

log = logging.getLogger(__name__)

LIVE_PATH = "/healthz/live"
READY_PATH = "/healthz/ready"
METRICS_PATH = "/metrics"

_TEXT_CONTENT_TYPE = "text/plain; charset=utf-8"
_REQUEST_TIMEOUT_SECONDS = 5.0
_MAX_HEADER_LINES = 100


class HealthServer:
    def __init__(self, port: int, is_ready: Callable[[], bool], metrics: WorkerMetrics, host: str = "0.0.0.0") -> None:
        self._host = host
        self._port = port
        self._is_ready = is_ready
        self._metrics = metrics
        self._server: asyncio.Server | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, self._host, self._port)
        log.info("Sağlık adresi %d portunda dinleniyor", self.port)

    @property
    def port(self) -> int:
        """Sunucunun gerçekten dinlediği port (0 verildiyse işletim sisteminin seçtiği)."""
        if self._server is None:
            raise RuntimeError("Sağlık sunucusu başlatılmadı")
        port: int = self._server.sockets[0].getsockname()[1]
        return port

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    def _respond(self, path: str) -> tuple[str, str, bytes]:
        """Durum satırı, içerik türü ve gövde."""
        if path == LIVE_PATH:
            # Süreç yanıt verebiliyorsa ayaktadır.
            return "200 OK", _TEXT_CONTENT_TYPE, b"ok"
        if path == READY_PATH:
            if self._is_ready():
                return "200 OK", _TEXT_CONTENT_TYPE, b"ready"
            return "503 Service Unavailable", _TEXT_CONTENT_TYPE, b"not ready"
        if path == METRICS_PATH:
            # Prometheus 3, içerik türünü tanımadığı yanıtı okumaz; bu yüzden kütüphanenin türü gönderilir.
            return "200 OK", WorkerMetrics.CONTENT_TYPE, self._metrics.render()
        return "404 Not Found", _TEXT_CONTENT_TYPE, b"not found"

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            # Yarım kalan veya kopan bir sağlık isteği işçiyi etkilememeli; bu iki hata yok sayılır.
            with contextlib.suppress(TimeoutError, ConnectionError):
                async with asyncio.timeout(_REQUEST_TIMEOUT_SECONDS):
                    request_line = await reader.readline()
                    # Başlıklar okunmadan bağlantı kapatılırsa istemci yanıtı alamayabilir.
                    for _ in range(_MAX_HEADER_LINES):
                        line = await reader.readline()
                        if line in (b"\r\n", b"\n", b""):
                            break

                    parts = request_line.decode("latin-1").split()
                    path = parts[1] if len(parts) >= 2 else ""
                    status, content_type, body = self._respond(path)
                    head = (
                        f"HTTP/1.1 {status}\r\n"
                        f"Content-Type: {content_type}\r\n"
                        f"Content-Length: {len(body)}\r\n"
                        "Connection: close\r\n"
                        "\r\n"
                    )
                    writer.write(head.encode("ascii") + body)
                    await writer.drain()
        finally:
            writer.close()
            with contextlib.suppress(ConnectionError):
                await writer.wait_closed()
