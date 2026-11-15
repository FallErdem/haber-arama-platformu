"""Beslemelerin indirilmesi (ADR-0013, 3. ve 4. bölüm).

Bir besleme adresine tek bir istek atar ve sonucu üç durumdan biri olarak döner: içerik geldi,
içerik değişmemiş ya da indirme başarısız. Hata fırlatmaz; ne yapılacağına (yeniden deneme,
erteleme, devre dışı bırakma) toplama akışı karar verir.
"""

import asyncio
from dataclasses import dataclass
from enum import StrEnum

import httpx

# En fazla bu kadar yönlendirme takip edilir (ADR-0013).
MAX_REDIRECTS = 3

_NOT_MODIFIED = 304
_UNAUTHORIZED = 401
_FORBIDDEN = 403
_TOO_MANY_REQUESTS = 429


class FailureKind(StrEnum):
    # Kaynak erişimi reddetti (401, 403). Aşılmaya çalışılmaz (FG-VT-06).
    BLOCKED = "BLOCKED"
    # Kaynak çok sık istek atıldığını bildirdi (429).
    RATE_LIMITED = "RATE_LIMITED"
    # Diğer hata kodları (404, 500 gibi).
    HTTP_ERROR = "HTTP_ERROR"
    # Yanıt alınamadı: bağlantı kurulamadı, zaman aşımı, çok fazla yönlendirme.
    NETWORK_ERROR = "NETWORK_ERROR"


@dataclass(frozen=True)
class FetchedFeed:
    body: bytes
    http_status: int
    # Yönlendirmeler takip edildikten sonra varılan adres.
    final_url: str
    # Bir sonraki istekte "değişti mi?" diye sormak için saklanır; kaynak vermediyse None.
    etag: str | None
    last_modified: str | None


@dataclass(frozen=True)
class FeedNotModified:
    """Kaynak "son okuduğundan beri değişmedi" dedi (304); içerik gönderilmedi."""

    http_status: int
    final_url: str


@dataclass(frozen=True)
class FetchFailed:
    kind: FailureKind
    message: str
    http_status: int | None = None
    final_url: str | None = None
    # Kaynak 429 ile birlikte kaç saniye beklenmesini istediyse (Retry-After).
    retry_after_seconds: float | None = None


type FetchResult = FetchedFeed | FeedNotModified | FetchFailed


def create_http_client(user_agent: str, timeout_seconds: float) -> httpx.AsyncClient:
    """Bütün indirmelerin paylaştığı HTTP istemcisini kurar.

    - User-Agent: işçi kendini kendi adıyla tanıtır; tarayıcı gibi görünmeye çalışmaz (FG-VT-05).
    - timeout: bağlanma, yanıtı bekleme gibi her aşama için ayrı ayrı uygulanır.
    """
    return httpx.AsyncClient(
        headers={"User-Agent": user_agent},
        follow_redirects=True,
        max_redirects=MAX_REDIRECTS,
        timeout=httpx.Timeout(timeout_seconds),
    )


class FeedFetcher:
    def __init__(self, client: httpx.AsyncClient, total_timeout_seconds: float) -> None:
        self._client = client
        # httpx'in zaman aşımı aşama başınadır; çok yavaş ama hiç durmayan bir yanıt onu aşmaz.
        # Bu değer bir indirmenin baştan sona en fazla ne kadar sürebileceğini sınırlar.
        self._total_timeout_seconds = total_timeout_seconds

    async def fetch(self, url: str, etag: str | None = None, last_modified: str | None = None) -> FetchResult:
        """Beslemeyi indirir. `etag` ve `last_modified` önceki başarılı indirmeden kalan değerlerdir."""
        # Koşullu istek: kaynak içeriğin değişmediğini görürse gövde göndermeden 304 döner.
        headers: dict[str, str] = {}
        if etag is not None:
            headers["If-None-Match"] = etag
        if last_modified is not None:
            headers["If-Modified-Since"] = last_modified

        try:
            async with asyncio.timeout(self._total_timeout_seconds):
                response = await self._client.get(url, headers=headers)
        except TimeoutError:
            return FetchFailed(FailureKind.NETWORK_ERROR, f"İndirme {self._total_timeout_seconds:g} saniyede bitmedi")
        except httpx.TooManyRedirects:
            return FetchFailed(FailureKind.NETWORK_ERROR, f"{MAX_REDIRECTS} yönlendirmeden fazlası takip edilmedi")
        except httpx.HTTPError as error:
            # Bağlantı hataları ve httpx'in aşama zaman aşımları. Hata sınıfının adı nedeni söyler
            # (ConnectTimeout, ReadTimeout, ConnectError gibi).
            return FetchFailed(FailureKind.NETWORK_ERROR, f"{type(error).__name__}: {error}".rstrip(": "))

        status = response.status_code
        final_url = str(response.url)
        if status == _NOT_MODIFIED:
            return FeedNotModified(http_status=status, final_url=final_url)
        if response.is_success:
            return FetchedFeed(
                body=response.content,
                http_status=status,
                final_url=final_url,
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
            )
        if status in (_UNAUTHORIZED, _FORBIDDEN):
            return FetchFailed(FailureKind.BLOCKED, f"Kaynak erişimi reddetti (HTTP {status})", status, final_url)
        if status == _TOO_MANY_REQUESTS:
            return FetchFailed(
                FailureKind.RATE_LIMITED,
                "Kaynak istek sınırının aşıldığını bildirdi (HTTP 429)",
                status,
                final_url,
                _retry_after_seconds(response.headers.get("Retry-After")),
            )
        return FetchFailed(FailureKind.HTTP_ERROR, f"Beklenmeyen yanıt (HTTP {status})", status, final_url)


def _retry_after_seconds(value: str | None) -> float | None:
    """Retry-After başlığını saniyeye çevirir. Başlık tarih biçiminde de gelebilir; o durumda None döner."""
    if value is None or not value.strip().isdigit():
        return None
    return float(value.strip())
