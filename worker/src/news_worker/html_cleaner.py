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

# Kaynak sitelerin metne gömdüğü ve haberin parçası olmayan kutuların sınıfları. Bu sınıflardan birini
# taşıyan etiket içindekilerle birlikte atılır; temizlik görseller toplanmadan önce yapılır.
# - mceNonEditable: Milliyet'in haber editörünün (TinyMCE) düzenlenemez blokları. Görsel yer tutucuları
#   ("Infografik Görsel (Quality Image)"; görselin adresi verilmez), ilgili haberler ve reklam kutularıdır.
# - inline-related: BirGün'ün "İlgili haberler" kutusu; içindeki küçük resimler başka haberlerin görselleridir.
_EMBEDDED_BLOCK_CLASSES = frozenset({"mceNonEditable", "inline-related"})


@dataclass(frozen=True)
class CleanedContent:
    # Temizlenmiş HTML; <img> içermez.
    html: str
    # İçerikteki görsellerin adresleri, içerikteki sırasıyla ve tekrarsız.
    image_urls: tuple[str, ...]


def clean_content(html: str, base_url: str | None = None) -> CleanedContent:
    """İçeriği temizler ve içindeki görsellerin adreslerini ayırır.

    `base_url` (haberin adresi) verilirse göreli bağlantılar ona göre tam adrese çevrilir: içerik
    bizim sitemizde gösterildiği için `/haber/...` gibi bir bağlantı kaynağa değil bize giderdi.
    """
    html = _remove_embedded_blocks(html)
    collector = _ImageUrlCollector()
    collector.feed(html)
    collector.close()
    return CleanedContent(
        html=nh3.clean(
            html, tags=_CONTENT_TAGS, url_relative=("rewrite_with_base", base_url) if base_url else None
        ).strip(),
        # dict.fromkeys: sırayı koruyarak tekrarları atar.
        image_urls=tuple(dict.fromkeys(collector.urls)),
    )


def to_plain_text(html: str) -> str:
    """HTML'den yalnızca yazıyı çıkarır; başlık ve özet gibi düz metin alanları için."""
    # Önce temizlik: betik ve stil etiketleri içerikleriyle birlikte gider, yazıya karışmaz.
    collector = _TextCollector()
    collector.feed(nh3.clean(_remove_embedded_blocks(html)))
    collector.close()
    return _WHITESPACE.sub(" ", "".join(collector.parts)).strip()


def _remove_embedded_blocks(html: str) -> str:
    """Haberin parçası olmayan gömülü kutuları (bkz. `_EMBEDDED_BLOCK_CLASSES`) içerikleriyle birlikte çıkarır."""
    finder = _EmbeddedBlockFinder(html)
    finder.feed(html)
    finder.close()
    # Sondan başa doğru kesilir; böylece öndeki kesimler arkadakilerin konumunu kaydırmaz.
    for start, end in reversed(finder.ranges):
        html = html[:start] + html[end:]
    return html


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


class _EmbeddedBlockFinder(HTMLParser):
    """Gömülü kutuların HTML metnindeki yerlerini (başlangıç, bitiş) bulur.

    Kutunun içinde aynı adlı etiket olabilir (<section> içinde <section>); kutu, açılan her iç etiket
    kapandıktan sonra gelen kendi kapanışında biter. Kapanmayan kutu atılmaz.
    """

    def __init__(self, html: str) -> None:
        # convert_charrefs=False: `&amp;` gibi kodlar ayrı parçalar olarak gelir; konum hesabı bozulmaz.
        super().__init__(convert_charrefs=False)
        self._html = html
        # HTMLParser konumu (satır, sütun) olarak verir; satırların başladığı yerden mutlak konum bulunur.
        self._line_starts = [0] + [match.end() for match in re.finditer("\n", html)]
        self.ranges: list[tuple[int, int]] = []
        self._block_tag: str | None = None
        self._depth = 0
        self._block_start = 0

    def _position(self) -> int:
        line, column = self.getpos()
        return self._line_starts[line - 1] + column

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._block_tag is not None:
            if tag == self._block_tag:
                self._depth += 1
            return
        classes = (dict(attrs).get("class") or "").split()
        if _EMBEDDED_BLOCK_CLASSES.intersection(classes):
            self._block_tag = tag
            self._depth = 1
            self._block_start = self._position()

    def handle_endtag(self, tag: str) -> None:
        if tag != self._block_tag:
            return
        self._depth -= 1
        if self._depth == 0:
            # Konum kapanış etiketinin başıdır (`</section>`); kesim etiketin sonundaki `>` işaretinden sonra biter.
            end = self._html.index(">", self._position()) + 1
            self.ranges.append((self._block_start, end))
            self._block_tag = None


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
