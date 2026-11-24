import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from news_worker.feed_reader import FeedParseError
from news_worker.nyt_reader import NytTopStoriesReader
from news_worker.parsed_article import ItemType

FIXTURES = Path(__file__).parent / "fixtures" / "feeds"


def valid_item(**changes: Any) -> dict[str, Any]:
    """Top Stories yanıtındaki bir haber; testler yalnızca değiştirdikleri alanı verir."""
    item: dict[str, Any] = {
        "section": "world",
        "title": "Örnek haber",
        "abstract": "Haberin özeti.",
        "url": "https://www.nytimes.com/2026/11/24/world/ornek.html",
        "uri": "nyt://article/ornek",
        "byline": "By Ali Veli",
        "published_date": "2026-11-24T07:00:00-05:00",
        "multimedia": [],
    }
    item.update(changes)
    return item


def top_stories(*items: dict[str, Any], status: str = "OK") -> bytes:
    return json.dumps({"status": status, "results": list(items)}).encode()


def image(url: str, width: int) -> dict[str, Any]:
    return {"url": url, "format": "x", "width": width, "height": width // 2, "type": "image"}


def test_top_stories_item_is_converted_to_common_structure() -> None:
    """Gerçek yanıttaki haber ortak yapıya çevrilir; yazar NYT'nin yazdığı gibi kalır (ADR-0009)."""
    article = NytTopStoriesReader().read((FIXTURES / "nyt-world.json").read_bytes()).articles[0]

    assert article.external_id == "nyt://article/415ac0a1-72ee-549f-978f-2cda6341673a"
    assert (
        article.url
        == "https://www.nytimes.com/2026/11/24/world/middleeast/iran-singer-parastoo-ahmadi-flogging-lashes.html"
    )
    assert article.normalized_url == article.url
    assert article.title == "Woman in Iran Lashed 74 Times for Singing With No Hijab"
    assert article.summary is not None and article.summary.startswith("Parastoo Ahmadi sang without wearing")
    assert article.content is None
    assert article.author == "By Ephrat Livni and Leily Nikounazar"
    assert article.item_type is ItemType.ARTICLE


def test_new_york_time_is_converted_to_utc() -> None:
    """NYT tarihi New York saatiyle verir (-05:00); UTC'ye çevrilir."""
    article = NytTopStoriesReader().read((FIXTURES / "nyt-world.json").read_bytes()).articles[0]

    assert article.published_at == datetime(2026, 11, 24, 12, 34, 52, tzinfo=UTC)


def test_category_comes_from_each_items_own_section() -> None:
    """Bir bölümün yanıtında başka bölümlerin haberleri de bulunur; kategori haberin kendi bölümünden bulunur."""
    articles = NytTopStoriesReader().read((FIXTURES / "nyt-world.json").read_bytes()).articles

    assert [article.source_categories for article in articles] == [("world",), ("business",), ("climate",)]


def test_only_the_largest_image_is_taken() -> None:
    """NYT aynı görseli birkaç boyutta verir; yalnızca en büyüğü alınır (sıradan bağımsız)."""
    item = valid_item(
        multimedia=[
            image("https://static01.nyt.com/orta.jpg", 600),
            image("https://static01.nyt.com/buyuk.jpg", 2048),
            image("https://static01.nyt.com/kucuk.jpg", 150),
        ]
    )

    article = NytTopStoriesReader().read(top_stories(item)).articles[0]

    assert article.image_urls == ("https://static01.nyt.com/buyuk.jpg",)


def test_item_without_image_has_no_image() -> None:
    """Görseli olmayan haberde `multimedia` boş ya da null gelir."""
    articles = (
        NytTopStoriesReader()
        .read(top_stories(valid_item(multimedia=None), valid_item(uri="nyt://article/iki", multimedia=[])))
        .articles
    )

    assert [article.image_urls for article in articles] == [(), ()]


def test_empty_byline_and_abstract_are_stored_as_missing() -> None:
    """Boş yazar ve özet boş metin olarak değil, yok olarak saklanır."""
    article = NytTopStoriesReader().read(top_stories(valid_item(byline="", abstract=""))).articles[0]

    assert article.author is None
    assert article.summary is None


def test_video_url_is_a_video() -> None:
    """Adresinin yolu `/video/` ile başlayan haber videodur (RSS okuyucusuyla aynı kural)."""
    item = valid_item(url="https://www.nytimes.com/video/world/100000000000/ornek.html")

    assert NytTopStoriesReader().read(top_stories(item)).articles[0].item_type is ItemType.VIDEO


def test_items_missing_required_fields_are_skipped_and_counted() -> None:
    """Kimliği, başlığı, geçerli adresi veya okunabilir tarihi olmayan haber atlanır ve sayılır."""
    result = NytTopStoriesReader().read(
        top_stories(
            valid_item(uri=""),
            valid_item(title=""),
            valid_item(url="javascript:alert(1)"),
            valid_item(published_date="dün"),
            valid_item(uri="nyt://article/gecerli"),
        )
    )

    assert [article.external_id for article in result.articles] == ["nyt://article/gecerli"]
    assert result.skipped_count == 4


@pytest.mark.parametrize("body", [b"", b"<html>Hata</html>", b"[]", b'{"results": []}'])
def test_unrecognized_response_raises_parse_error(body: bytes) -> None:
    """JSON olmayan ya da beklenen yapıda olmayan yanıt okuma hatasıdır."""
    with pytest.raises(FeedParseError):
        NytTopStoriesReader().read(body)


def test_ok_response_without_results_is_empty_not_an_error() -> None:
    """Haber içermeyen bölüm (`sports`: Nisan 2025'ten beri boş) "OK" ile `results: null` döner; sıfır haberdir."""
    body = json.dumps({"status": "OK", "num_results": 0, "results": None}).encode()

    result = NytTopStoriesReader().read(body)

    assert result.articles == ()
    assert result.skipped_count == 0


def test_response_with_error_status_raises_parse_error() -> None:
    """`status` alanı "OK" değilse yanıt haber listesi sayılmaz."""
    with pytest.raises(FeedParseError, match="ERROR"):
        NytTopStoriesReader().read(top_stories(valid_item(), status="ERROR"))
