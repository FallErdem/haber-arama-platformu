import asyncio
from collections.abc import AsyncIterator

import httpx
import pytest
import respx

from news_worker.feed_fetcher import (
    MAX_REDIRECTS,
    FailureKind,
    FeedFetcher,
    FeedNotModified,
    FetchedFeed,
    FetchFailed,
    create_http_client,
)

FEED_URL = "https://example.test/feed.rss"
USER_AGENT = "HaberAramaPlatformuTest/0.1"
BODY = b"<rss version='2.0'><channel></channel></rss>"


@pytest.fixture
async def fetcher() -> AsyncIterator[FeedFetcher]:
    """Gerçek ayarlarla kurulmuş istemci; istekler respx tarafından karşılanır, ağa çıkılmaz."""
    async with create_http_client(USER_AGENT, timeout_seconds=5) as client:
        yield FeedFetcher(client, total_timeout_seconds=0.2)


async def test_successful_download_returns_body_and_validators(
    fetcher: FeedFetcher, respx_mock: respx.MockRouter
) -> None:
    """Başarılı indirmede içerik ve bir sonraki koşullu istek için saklanacak değerler döner."""
    respx_mock.get(FEED_URL).respond(
        200, content=BODY, headers={"ETag": '"abc"', "Last-Modified": "Sun, 15 Nov 2026 10:00:00 GMT"}
    )

    result = await fetcher.fetch(FEED_URL)

    assert result == FetchedFeed(
        body=BODY,
        http_status=200,
        final_url=FEED_URL,
        etag='"abc"',
        last_modified="Sun, 15 Nov 2026 10:00:00 GMT",
    )


async def test_missing_validators_are_none(fetcher: FeedFetcher, respx_mock: respx.MockRouter) -> None:
    """Kaynak ETag ve Last-Modified vermiyorsa değerler boş döner."""
    respx_mock.get(FEED_URL).respond(200, content=BODY)

    result = await fetcher.fetch(FEED_URL)

    assert isinstance(result, FetchedFeed)
    assert result.etag is None
    assert result.last_modified is None


async def test_worker_identifies_itself_with_its_own_user_agent(
    fetcher: FeedFetcher, respx_mock: respx.MockRouter
) -> None:
    """İşçi kendini kendi adıyla tanıtır (FG-VT-05)."""
    route = respx_mock.get(FEED_URL).respond(200, content=BODY)

    await fetcher.fetch(FEED_URL)

    assert route.calls.last.request.headers["User-Agent"] == USER_AGENT


async def test_conditional_headers_are_sent_when_validators_are_known(
    fetcher: FeedFetcher, respx_mock: respx.MockRouter
) -> None:
    """Önceki indirmeden kalan değerler koşullu istek başlıkları olarak gönderilir."""
    route = respx_mock.get(FEED_URL).respond(304)

    await fetcher.fetch(FEED_URL, etag='"abc"', last_modified="Sun, 15 Nov 2026 10:00:00 GMT")

    headers = route.calls.last.request.headers
    assert headers["If-None-Match"] == '"abc"'
    assert headers["If-Modified-Since"] == "Sun, 15 Nov 2026 10:00:00 GMT"


async def test_conditional_headers_are_not_sent_on_first_download(
    fetcher: FeedFetcher, respx_mock: respx.MockRouter
) -> None:
    """İlk indirmede saklanmış değer yoktur; koşullu istek başlığı gönderilmez."""
    route = respx_mock.get(FEED_URL).respond(200, content=BODY)

    await fetcher.fetch(FEED_URL)

    headers = route.calls.last.request.headers
    assert "If-None-Match" not in headers
    assert "If-Modified-Since" not in headers


async def test_not_modified_response_is_reported(fetcher: FeedFetcher, respx_mock: respx.MockRouter) -> None:
    """304 yanıtı "değişmedi" olarak döner; bu bir hata değildir."""
    respx_mock.get(FEED_URL).respond(304)

    result = await fetcher.fetch(FEED_URL, etag='"abc"')

    assert result == FeedNotModified(http_status=304, final_url=FEED_URL)


@pytest.mark.parametrize("status", [401, 403])
async def test_access_denial_is_reported_and_not_retried(
    fetcher: FeedFetcher, respx_mock: respx.MockRouter, status: int
) -> None:
    """Erişim engeli aşılmaya çalışılmaz: tek istek atılır ve sonuç "engellendi" olarak döner (FG-VT-06)."""
    route = respx_mock.get(FEED_URL).respond(status)

    result = await fetcher.fetch(FEED_URL)

    assert isinstance(result, FetchFailed)
    assert result.kind is FailureKind.BLOCKED
    assert result.http_status == status
    assert route.call_count == 1


async def test_rate_limit_response_carries_retry_after(fetcher: FeedFetcher, respx_mock: respx.MockRouter) -> None:
    """429 yanıtında kaynağın istediği bekleme süresi okunur."""
    respx_mock.get(FEED_URL).respond(429, headers={"Retry-After": "120"})

    result = await fetcher.fetch(FEED_URL)

    assert isinstance(result, FetchFailed)
    assert result.kind is FailureKind.RATE_LIMITED
    assert result.retry_after_seconds == 120.0


@pytest.mark.parametrize("headers", [{}, {"Retry-After": "Sun, 15 Nov 2026 10:00:00 GMT"}], ids=["missing", "date"])
async def test_rate_limit_without_seconds_has_no_retry_after(
    fetcher: FeedFetcher, respx_mock: respx.MockRouter, headers: dict[str, str]
) -> None:
    """Bekleme süresi verilmemişse veya tarih biçimindeyse süre boş döner."""
    respx_mock.get(FEED_URL).respond(429, headers=headers)

    result = await fetcher.fetch(FEED_URL)

    assert isinstance(result, FetchFailed)
    assert result.kind is FailureKind.RATE_LIMITED
    assert result.retry_after_seconds is None


@pytest.mark.parametrize("status", [404, 500, 503])
async def test_other_error_statuses_are_http_errors(
    fetcher: FeedFetcher, respx_mock: respx.MockRouter, status: int
) -> None:
    """Diğer hata kodları durum koduyla birlikte "HTTP hatası" olarak döner."""
    respx_mock.get(FEED_URL).respond(status)

    result = await fetcher.fetch(FEED_URL)

    assert isinstance(result, FetchFailed)
    assert result.kind is FailureKind.HTTP_ERROR
    assert result.http_status == status


async def test_redirect_is_followed_and_final_url_is_reported(
    fetcher: FeedFetcher, respx_mock: respx.MockRouter
) -> None:
    """Yönlendirme takip edilir; varılan adres sonuçta yer alır."""
    moved_url = "https://example.test/yeni-feed.rss"
    respx_mock.get(FEED_URL).respond(301, headers={"Location": moved_url})
    respx_mock.get(moved_url).respond(200, content=BODY)

    result = await fetcher.fetch(FEED_URL)

    assert isinstance(result, FetchedFeed)
    assert result.final_url == moved_url


async def test_more_redirects_than_allowed_is_a_failure(fetcher: FeedFetcher, respx_mock: respx.MockRouter) -> None:
    """İzin verilenden fazla yönlendirme takip edilmez."""
    # Her adres bir sonrakine yönlendirir: izin verilen sayıdan bir fazla yönlendirme.
    for step in range(MAX_REDIRECTS + 1):
        respx_mock.get(f"https://example.test/{step}").respond(
            302, headers={"Location": f"https://example.test/{step + 1}"}
        )

    result = await fetcher.fetch("https://example.test/0")

    assert isinstance(result, FetchFailed)
    assert result.kind is FailureKind.NETWORK_ERROR
    assert "yönlendirme" in result.message


async def test_connection_problem_is_a_network_error(fetcher: FeedFetcher, respx_mock: respx.MockRouter) -> None:
    """Bağlantı kurulamazsa hata fırlatılmaz; nedeniyle birlikte "ağ hatası" döner."""
    respx_mock.get(FEED_URL).mock(side_effect=httpx.ConnectTimeout("bağlantı zaman aşımı"))

    result = await fetcher.fetch(FEED_URL)

    assert isinstance(result, FetchFailed)
    assert result.kind is FailureKind.NETWORK_ERROR
    assert "ConnectTimeout" in result.message
    assert result.http_status is None


async def test_download_slower_than_total_timeout_is_a_network_error(
    fetcher: FeedFetcher, respx_mock: respx.MockRouter
) -> None:
    """Toplam süre sınırını aşan indirme yarıda kesilir."""

    async def slow_response(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(5)
        return httpx.Response(200, content=BODY)

    respx_mock.get(FEED_URL).mock(side_effect=slow_response)

    result = await fetcher.fetch(FEED_URL)

    assert isinstance(result, FetchFailed)
    assert result.kind is FailureKind.NETWORK_ERROR
    assert "bitmedi" in result.message
