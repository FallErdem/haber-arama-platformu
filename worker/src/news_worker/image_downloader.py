"""Görsellerin indirilmesi ve doğrulanması (ADR-0013, 5. bölüm; FG-VT-14).

Görsel dışarıdan gelir ve güvenilmez: adresi bir görsel yerine HTML sayfası, bozuk bir dosya veya
çok büyük bir dosya döndürebilir. Dosya indirildikten sonra Pillow ile gerçekten açılmaya çalışılır;
türü, sunucunun söylediğine göre değil dosyanın kendisine göre belirlenir.
"""

import asyncio
import io
from dataclasses import dataclass

import httpx
from PIL import Image, UnidentifiedImageError

# 20 MB'tan büyük dosyalar alınmaz (İ-14 kabul ölçütü). Haber görselleri genellikle 100 KB – 2 MB'tır.
MAX_IMAGE_BYTES = 20 * 1024 * 1024

# Kabul edilen görsel türleri: Pillow'un adı -> saklanan ve sunulan içerik türü.
ALLOWED_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "GIF": "image/gif",
}

# Bu durumlarda görsel bir daha denenmez: kaynak görselin artık olmadığını söylüyor.
_GONE_STATUSES = frozenset({404, 410})


@dataclass(frozen=True)
class DownloadedImage:
    body: bytes
    content_type: str
    width: int
    height: int


@dataclass(frozen=True)
class DownloadFailed:
    message: str
    # True: yeniden denemek sonucu değiştirmez (404, görsel değil, çok büyük).
    # False: geçici olabilir (ağ hatası, zaman aşımı, 5xx, 403, 429); daha sonra yeniden denenir.
    permanent: bool


type DownloadResult = DownloadedImage | DownloadFailed


class NotAnImageError(Exception):
    """Dosya kabul edilen türlerden bir görsel olarak açılamadı."""


@dataclass(frozen=True)
class ImageInfo:
    content_type: str
    width: int
    height: int


def inspect_image(body: bytes) -> ImageInfo:
    """Dosyanın gerçekten kabul edilen türde bir görsel olduğunu doğrular; türünü ve boyutlarını döner.

    `verify()` dosyanın yapısını baştan sona denetler ama piksel verisini belleğe açmaz. Pillow,
    boyutları aşırı büyük bildirilen dosyaları (sıkıştırılmış küçük bir dosyanın açılınca belleği
    doldurması, "decompression bomb") kendisi reddeder.
    """
    try:
        with Image.open(io.BytesIO(body)) as image:
            image_format = image.format
            width, height = image.size
            image.verify()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError, ValueError) as error:
        raise NotAnImageError(f"Görsel olarak açılamadı: {type(error).__name__}") from None
    content_type = ALLOWED_FORMATS.get(image_format or "")
    if content_type is None:
        raise NotAnImageError(f"Kabul edilmeyen görsel türü: {image_format}")
    return ImageInfo(content_type=content_type, width=width, height=height)


class ImageDownloader:
    def __init__(
        self, client: httpx.AsyncClient, total_timeout_seconds: float, max_bytes: int = MAX_IMAGE_BYTES
    ) -> None:
        # Besleme indirmeleriyle aynı istemci: aynı User-Agent, aynı yönlendirme ve zaman sınırları.
        self._client = client
        self._total_timeout_seconds = total_timeout_seconds
        self._max_bytes = max_bytes

    async def download(self, url: str) -> DownloadResult:
        """Görseli indirir ve doğrular. Hata fırlatmaz; ne yapılacağına çağıran karar verir.

        Adresteki Türkçe karakterleri (`güllü-davası.jpg`) httpx kendisi kodlar (`g%C3%BCll%C3%BC`).
        """
        try:
            async with asyncio.timeout(self._total_timeout_seconds):
                body = await self._fetch(url)
        except _Rejected as rejected:
            return rejected.failure
        except TimeoutError:
            return DownloadFailed(f"Zaman aşımı ({self._total_timeout_seconds:.0f} sn)", permanent=False)
        except httpx.HTTPError as error:
            return DownloadFailed(f"Ağ hatası: {type(error).__name__}", permanent=False)

        try:
            # Doğrulama işlemciyi kullanır; ayrı bir iş parçacığında yapılır ki diğer işler beklemesin.
            info = await asyncio.to_thread(inspect_image, body)
        except NotAnImageError as error:
            return DownloadFailed(str(error), permanent=True)
        return DownloadedImage(body=body, content_type=info.content_type, width=info.width, height=info.height)

    async def _fetch(self, url: str) -> bytes:
        # stream: yanıt parça parça okunur; sınırı aşan dosyanın tamamı belleğe alınmadan kesilir.
        async with self._client.stream("GET", url) as response:
            if response.status_code in _GONE_STATUSES:
                raise _Rejected(DownloadFailed(f"HTTP {response.status_code}", permanent=True))
            if response.status_code != httpx.codes.OK:
                raise _Rejected(DownloadFailed(f"HTTP {response.status_code}", permanent=False))

            # Sunucu boyutu baştan söylediyse dosya hiç indirilmez.
            declared = response.headers.get("Content-Length")
            if declared is not None and declared.isdigit() and int(declared) > self._max_bytes:
                raise _Rejected(self._too_large())

            chunks: list[bytes] = []
            size = 0
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                # Boyut bildirilmemiş veya yanlış bildirilmiş olabilir; okunan miktar da sayılır.
                if size > self._max_bytes:
                    raise _Rejected(self._too_large())
                chunks.append(chunk)
            return b"".join(chunks)

    def _too_large(self) -> DownloadFailed:
        return DownloadFailed(f"Dosya {self._max_bytes // (1024 * 1024)} MB sınırından büyük", permanent=True)


class _Rejected(Exception):
    """İndirmenin bir sonuçla erken bitirildiğini bildirir; yalnızca bu modülün içinde kullanılır."""

    def __init__(self, failure: DownloadFailed) -> None:
        super().__init__(failure.message)
        self.failure = failure
