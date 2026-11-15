"""Kaynaklardan gelen HTML'in temizlenmesi (FOG-16).

Besleme içeriği dışarıdan gelir ve güvenilmez: içinde betik, olay özniteliği veya zararlı bağlantı
bulunabilir. İçerik saklanmadan önce burada temizlenir; görseller ayrıca indirilip kendi depomuzdan
sunulduğu için <img> etiketleri içerikten çıkarılır ve adresleri ayrı döndürülür.
"""

import re
from dataclasses import dataclass
from html.parser import HTMLParser

import nh3

from news_worker.url_normalizer import is_http_url

# nh3'ün güvenli saydığı etiketler; görseller içerikte kalmaz.
_CONTENT_TAGS = nh3.ALLOWED_TAGS - {"img"}

# Düz metne çevirirken bu etiketlerin çevresine boşluk konur; yoksa art arda gelen
# paragrafların yazıları birbirine yapışır ("Birinci.İkinci.").
_BLOCK_TAGS = frozenset(
    {
        "article",
        "aside",
        "blockquote",
        "br",
        "dd",
        "div",
        "dt",
        "figcaption",
        "figure",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "p",
        "pre",
        "table",
        "td",
        "th",
        "tr",
    }
)

_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class CleanedContent:
    # Temizlenmiş HTML; <img> içermez.
    html: str
    # İçerikteki görsellerin adresleri, içerikteki sırasıyla ve tekrarsız.
    image_urls: tuple[str, ...]


def clean_content(html: str) -> CleanedContent:
    """İçeriği temizler ve içindeki görsellerin adreslerini ayırır."""
    collector = _ImageUrlCollector()
    collector.feed(html)
    collector.close()
    return CleanedContent(
        html=nh3.clean(html, tags=_CONTENT_TAGS).strip(),
        # dict.fromkeys: sırayı koruyarak tekrarları atar.
        image_urls=tuple(dict.fromkeys(collector.urls)),
    )


def to_plain_text(html: str) -> str:
    """HTML'den yalnızca yazıyı çıkarır; başlık ve özet gibi düz metin alanları için."""
    # Önce temizlik: betik ve stil etiketleri içerikleriyle birlikte gider, yazıya karışmaz.
    collector = _TextCollector()
    collector.feed(nh3.clean(html))
    collector.close()
    return _WHITESPACE.sub(" ", "".join(collector.parts)).strip()


class _ImageUrlCollector(HTMLParser):
    """<img> etiketlerinin `src` adreslerini toplar."""

    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "img":
            return
        source = dict(attrs).get("src")
        if source is None:
            return
        url = source.strip()
        # Yalnızca indirilebilir adresler: `data:` veya `javascript:` ile başlayanlar alınmaz.
        if is_http_url(url):
            self.urls.append(url)


class _TextCollector(HTMLParser):
    """Etiketleri atıp aradaki yazıyı toplar. `&amp;` gibi kodları HTMLParser kendisi çözer."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _BLOCK_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in _BLOCK_TAGS:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)
