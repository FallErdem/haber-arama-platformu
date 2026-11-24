"""New York Times Top Stories API yanıtlarının okunması (ADR-0009).

Bir bölümün yanıtı (`/svc/topstories/v2/{bölüm}.json`) girer, RSS okuyucusuyla aynı `FeedReadResult`
çıkar; kaydetme, kategori ve görsel akışı iki kaynak türünde de aynıdır.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from news_worker.feed_reader import FeedParseError, FeedReadResult
from news_worker.html_cleaner import to_plain_text
from news_worker.parsed_article import ParsedArticle, item_type_of
from news_worker.url_normalizer import is_http_url, normalize_url

log = logging.getLogger(__name__)

# `sources.reader_type` değeri.
NYT_READER_TYPE = "NYT_TOP_STORIES"
# API anahtarının isteğe eklendiği adres parametresi (NYT'nin dokümantasyonundaki ad).
API_KEY_PARAMETER = "api-key"


class NytTopStoriesReader:
    def read(self, body: bytes, field_mapping: object = None, feed_time_zone: str | None = None) -> FeedReadResult:
        """Yanıtı haberlere çevirir. `field_mapping` ve `feed_time_zone` RSS okuyucusunun ayarlarıdır; burada
        kullanılmaz (iki okuyucu aynı biçimde çağrılır). Zorunlu alanı eksik haber atlanır ve sayılır."""
        try:
            data = json.loads(body)
        except ValueError:
            raise FeedParseError("Yanıt JSON olarak okunamadı") from None
        if not isinstance(data, dict):
            raise FeedParseError("Yanıt beklenen yapıda değil")
        if data.get("status") != "OK":
            raise FeedParseError(f"Yanıtın durumu OK değil: {data.get('status')!r}")
        results = data.get("results")
        # Haber içermeyen bölüm "OK" ile `results: null` döner (sports, Nisan 2025'ten beri); bu sıfır haberdir,
        # hata değil (boş RSS beslemesi gibi).
        if results is None:
            results = []
        if not isinstance(results, list):
            raise FeedParseError("Yanıttaki haber listesi (results) liste değil")

        articles: list[ParsedArticle] = []
        skipped_count = 0
        for item in results:
            article = _to_article(item) if isinstance(item, dict) else None
            if article is None:
                skipped_count += 1
            else:
                articles.append(article)

        if skipped_count:
            log.warning("Zorunlu alanı eksik olan %d haber atlandı", skipped_count)
        return FeedReadResult(articles=tuple(articles), skipped_count=skipped_count)


def _to_article(item: dict[str, Any]) -> ParsedArticle | None:
    """Yanıttaki haberi ortak yapıya çevirir; zorunlu bir alan eksikse None döner.

    Başlık, özet, yazar ve adres değiştirilmeden alınır (ADR-0009); yalnızca HTML'den arındırılır (FOG-16).
    """
    external_id = _text(item.get("uri"))
    url = _text(item.get("url"))
    title = to_plain_text(_text(item.get("title")) or "")
    published_at = _published_at(item.get("published_date"))
    if external_id is None or url is None or not is_http_url(url) or not title or published_at is None:
        return None

    section = _text(item.get("section"))
    return ParsedArticle(
        external_id=external_id,
        url=url,
        normalized_url=normalize_url(url),
        title=title,
        summary=to_plain_text(_text(item.get("abstract")) or "") or None,
        # Top Stories tam metin vermez.
        content=None,
        author=_text(item.get("byline")),
        published_at=published_at,
        item_type=item_type_of(url),
        image_urls=_largest_image(item.get("multimedia")),
        # Kategori, haberin kendi bölümünden bulunur: bir bölümün yanıtında başka bölümlerin haberleri de vardır.
        source_categories=(section,) if section else (),
    )


def _published_at(value: object) -> datetime | None:
    """Tarih ISO 8601 biçiminde, New York saatiyle gelir (`2026-11-24T07:34:52-05:00`); UTC'ye çevrilir."""
    if not isinstance(value, str):
        return None
    try:
        published_at = datetime.fromisoformat(value)
    except ValueError:
        return None
    if published_at.tzinfo is None:
        return None
    return published_at.astimezone(UTC)


def _largest_image(multimedia: object) -> tuple[str, ...]:
    """NYT aynı görseli birkaç boyutta verir (2048, 600 ve 150 piksel genişlikte); yalnızca en genişi alınır.

    Görsel bizde yine en uzun kenarı 1600 piksel olacak şekilde küçültülür (ADR-0017, 12. bölüm).
    """
    if not isinstance(multimedia, list):
        return ()
    candidates = [
        media
        for media in multimedia
        if isinstance(media, dict)
        and media.get("type") == "image"
        and isinstance(media.get("width"), int)
        and is_http_url(_text(media.get("url")) or "")
    ]
    if not candidates:
        return ()
    largest = max(candidates, key=lambda media: media["width"])
    return (largest["url"].strip(),)


def _text(value: object) -> str | None:
    """Boş olmayan metni kenar boşlukları atılmış olarak döner; metin değilse ya da boşsa None."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
