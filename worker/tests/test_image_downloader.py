"""Görsel indirme ve doğrulama testleri. Görsel siteleri `respx` ile taklit edilir; testler internete çıkmaz."""

from collections.abc import AsyncIterator

import httpx
import pytest
import respx
from conftest import make_image
from PIL import Image

from news_worker.feed_fetcher import create_http_client
from news_worker.image_downloader import (
    DownloadedImage,
    DownloadFailed,
    ImageDownloader,
    NotAnImageError,
    inspect_image,
)

IMAGE_URL = "https://images.example.test/haber.jpg"


# --- Doğrulama -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("image_format", "content_type"),
    [("JPEG", "image/jpeg"), ("PNG", "image/png"), ("WEBP", "image/webp"), ("GIF", "image/gif")],
)
def test_supported_image_is_recognized_with_its_type_and_size(image_format: str, content_type: str) -> None:
    """Kabul edilen türlerdeki görselin türü ve boyutları dosyanın kendisinden okunur."""
    info = inspect_image(make_image(image_format, size=(64, 48)))

    assert (info.content_type, info.width, info.height) == (content_type, 64, 48)


@pytest.mark.parametrize(
    "body",
    [
        b"<html><body>Sayfa bulunamadi</body></html>",
        b"",
        make_image("JPEG")[:50],
    ],
    ids=["html-page", "empty", "truncated-jpeg"],
)
def test_file_that_is_not_an_image_is_rejected(body: bytes) -> None:
    """HTML sayfası, boş dosya veya yarım kalmış görsel reddedilir."""
    with pytest.raises(NotAnImageError):
        inspect_image(body)


def test_image_of_unsupported_type_is_rejected() -> None:
    """Pillow'un açabildiği ama kabul etmediğimiz türler (BMP gibi) reddedilir."""
    with pytest.raises(NotAnImageError, match="BMP"):
        inspect_image(make_image("BMP"))


def test_decompression_bomb_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Açılınca belleği dolduracak kadar büyük boyut bildiren görsel reddedilir.

    Pillow'un sınırı yaklaşık 89 milyon piksel; testte gerçekten o büyüklükte dosya üretmemek için
    sınır küçültülür. Pillow, sınırın iki katını aşan görseli açmayı reddeder.
    """
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)

    with pytest.raises(NotAnImageError, match="DecompressionBomb"):
        inspect_image(make_image("PNG", size=(20, 20)))


# --- İndirme -------------------------------------------------------------------------------------


@pytest.fixture
async def downloader() -> ImageDownloader:
    return ImageDownloader(create_http_client("HaberAramaPlatformu/test", 5), total_timeout_seconds=5)


async def test_image_is_downloaded_and_inspected(downloader: ImageDownloader, respx_mock: respx.MockRouter) -> None:
    """Görsel indirilir; türü sunucunun bildirdiğine değil dosyanın kendisine göre belirlenir."""
    body = make_image("PNG", size=(80, 60))
    # Sunucu yanlış tür bildiriyor.
    respx_mock.get(IMAGE_URL).respond(200, content=body, headers={"Content-Type": "image/jpeg"})

    result = await downloader.download(IMAGE_URL)

    assert result == DownloadedImage(body=body, content_type="image/png", width=80, height=60)


async def test_address_with_turkish_letters_is_encoded(
    downloader: ImageDownloader, respx_mock: respx.MockRouter
) -> None:
    """Adresinde Türkçe karakter olan görsel (NTV) kodlanmış adresle istenir ve indirilir."""
    route = respx_mock.get("https://images.ntv.example.test/images/g%C3%BCll%C3%BC-davas%C4%B1-374847.jpg")
    route.respond(200, content=make_image())

    result = await downloader.download("https://images.ntv.example.test/images/güllü-davası-374847.jpg")

    assert isinstance(result, DownloadedImage)
    assert route.called


@pytest.mark.parametrize("status", [404, 410])
async def test_missing_image_is_a_permanent_failure(
    downloader: ImageDownloader, respx_mock: respx.MockRouter, status: int
) -> None:
    """Kaynak görselin artık olmadığını söylüyorsa (404, 410) yeniden denemeye gerek yoktur."""
    respx_mock.get(IMAGE_URL).respond(status)

    assert await downloader.download(IMAGE_URL) == DownloadFailed(f"HTTP {status}", permanent=True)


@pytest.mark.parametrize("status", [500, 503, 403, 429])
async def test_other_http_errors_are_temporary(
    downloader: ImageDownloader, respx_mock: respx.MockRouter, status: int
) -> None:
    """Sunucu hatası, erişim engeli veya istek sınırı geçici olabilir; daha sonra yeniden denenir."""
    respx_mock.get(IMAGE_URL).respond(status)

    assert await downloader.download(IMAGE_URL) == DownloadFailed(f"HTTP {status}", permanent=False)


async def test_network_error_is_temporary(downloader: ImageDownloader, respx_mock: respx.MockRouter) -> None:
    """Bağlantı kurulamazsa görsel daha sonra yeniden denenir."""
    respx_mock.get(IMAGE_URL).mock(side_effect=httpx.ConnectError("bağlanılamadı"))

    assert await downloader.download(IMAGE_URL) == DownloadFailed("Ağ hatası: ConnectError", permanent=False)


async def test_slow_download_is_stopped_and_retried_later(respx_mock: respx.MockRouter) -> None:
    """Toplam süre sınırını aşan indirme kesilir; geçici hata sayılır."""
    respx_mock.get(IMAGE_URL).mock(side_effect=httpx.ReadTimeout("yavaş"))
    downloader = ImageDownloader(create_http_client("HaberAramaPlatformu/test", 5), total_timeout_seconds=5)

    result = await downloader.download(IMAGE_URL)

    assert result == DownloadFailed("Ağ hatası: ReadTimeout", permanent=False)


async def test_html_page_instead_of_image_is_a_permanent_failure(
    downloader: ImageDownloader, respx_mock: respx.MockRouter
) -> None:
    """Adres görsel yerine bir sayfa döndürürse görsel bir daha denenmez."""
    respx_mock.get(IMAGE_URL).respond(200, content=b"<html>Haber</html>", headers={"Content-Type": "text/html"})

    result = await downloader.download(IMAGE_URL)

    assert isinstance(result, DownloadFailed)
    assert result.permanent is True


async def test_file_declared_larger_than_limit_is_not_downloaded(respx_mock: respx.MockRouter) -> None:
    """Sunucu dosyanın sınırdan büyük olduğunu baştan bildirirse dosya indirilmez."""
    downloader = ImageDownloader(create_http_client("t", 5), total_timeout_seconds=5, max_bytes=1024 * 1024)
    respx_mock.get(IMAGE_URL).respond(200, content=b"x" * 10, headers={"Content-Length": str(2 * 1024 * 1024)})

    assert await downloader.download(IMAGE_URL) == DownloadFailed("Dosya 1 MB sınırından büyük", permanent=True)


async def test_file_growing_past_limit_while_reading_is_stopped(respx_mock: respx.MockRouter) -> None:
    """Boyutu bildirilmemiş dosya okunurken sınırı aşarsa okuma kesilir; tamamı belleğe alınmaz."""
    downloader = ImageDownloader(create_http_client("t", 5), total_timeout_seconds=5, max_bytes=1024 * 1024)
    stream = ChunkedStream(count=10, chunk_size=512 * 1024)
    respx_mock.get(IMAGE_URL).respond(200, stream=stream)

    result = await downloader.download(IMAGE_URL)

    assert result == DownloadFailed("Dosya 1 MB sınırından büyük", permanent=True)
    # 1 MB sınırı üçüncü yarım megabaytlık parçada aşılır; geri kalan yedi parça okunmaz.
    assert stream.chunks_sent == 3


class ChunkedStream(httpx.AsyncByteStream):
    """Boyut başlığı göndermeden parça parça gelen yanıt; kaç parça okunduğunu sayar."""

    def __init__(self, count: int, chunk_size: int) -> None:
        self._count = count
        self._chunk_size = chunk_size
        self.chunks_sent = 0

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for _ in range(self._count):
            self.chunks_sent += 1
            yield b"x" * self._chunk_size
