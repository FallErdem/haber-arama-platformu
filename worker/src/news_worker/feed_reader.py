"""RSS ve Atom beslemelerinin okunması (ADR-0013).

Beslemenin metni girer, kaynaktan bağımsız `ParsedArticle` listesi çıkar. İndirme ve kaydetme
burada değildir (İ-12); bu yüzden okuyucu ağ ve veritabanı olmadan sınanabilir.
"""

import io
import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, tzinfo
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlsplit
from xml.etree import ElementTree
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import feedparser

from news_worker.html_cleaner import clean_content, to_plain_text
from news_worker.parsed_article import ItemType, ParsedArticle
from news_worker.url_normalizer import is_http_url, normalize_url

log = logging.getLogger(__name__)

# `sources.field_mapping` içindeki anahtar: haberin ana görselinin okunacağı etiketin adı.
# Örnek: CNN Türk ve Akşam için {"image": "image"}.
IMAGE_FIELD = "image"

# Bir haberi saran etiket: RSS'te <item>, Atom'da <entry>.
_ITEM_TAGS = frozenset({"item", "entry"})
# Adresi bu yolla başlayan haberler videodur (CNN Türk: /video/dunya/...).
_VIDEO_PATH_PREFIX = "/video/"
_IMAGE_TYPE_PREFIX = "image/"
# Özetin sonundaki "devamı" bağlantısının yazısı; haberin parçası değildir. Sabah her özetin sonuna
# haberin kendisine dönen "Devamı için tıklayınız" bağlantısı koyar.
_READ_MORE_SUFFIX = re.compile(r"\s*devamı için tıklayınız\s*$", re.IGNORECASE)


class FeedParseError(Exception):
    """Besleme okunamadı: gelen metin RSS veya Atom olarak tanınmadı (örneğin besleme yerine bir hata
    sayfası döndü) ya da kaynağın okuma ayarı geçersiz (tanınmayan saat dilimi adı)."""


@dataclass(frozen=True)
class FeedReadResult:
    articles: tuple[ParsedArticle, ...]
    # Zorunlu bir alanı (kimlik, adres, başlık, tarih) eksik olduğu için atlanan haber sayısı.
    skipped_count: int


class FeedReader:
    """RSS ve Atom okuyucusu. feedparser iki biçimi de aynı alan adlarıyla verdiği için tek sınıftır."""

    def read(
        self,
        body: bytes,
        field_mapping: Mapping[str, str] | None = None,
        feed_time_zone: str | None = None,
    ) -> FeedReadResult:
        """Beslemeyi okur. Boş besleme hata değildir; tanınmayan içerik `FeedParseError` fırlatır.

        `feed_time_zone` (`sources.feed_time_zone`): beslemedeki saatlerin gerçekte yazıldığı saat
        dilimi. Verilirse saatin yanındaki saat dilimi bilgisi yok sayılır. Saat dilimini yanlış
        yazan kaynaklar içindir: CNN Türk Türkiye saatini yazıp yanına "GMT" koyar.
        """
        time_zone = _time_zone(feed_time_zone) if feed_time_zone else None
        # BytesIO: feedparser'a düz metin verilirse onu bir adres veya dosya yolu sanıp açmayı
        # dener; dosya benzeri bir nesne verildiğinde yalnızca içeriğini okur.
        parsed = feedparser.parse(io.BytesIO(body))
        if not parsed.get("version"):
            raise FeedParseError("İçerik RSS veya Atom olarak tanınamadı")

        image_field = (field_mapping or {}).get(IMAGE_FIELD)
        custom_images = _read_custom_field(body, image_field) if image_field else {}

        articles: list[ParsedArticle] = []
        skipped_count = 0
        for entry in parsed.entries:
            article = _to_article(entry, custom_images, time_zone)
            if article is None:
                skipped_count += 1
            else:
                articles.append(article)

        if skipped_count:
            log.warning("Zorunlu alanı eksik olan %d haber atlandı", skipped_count)
        return FeedReadResult(articles=tuple(articles), skipped_count=skipped_count)


def _time_zone(name: str) -> tzinfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise FeedParseError(f"Kaynağın saat dilimi ayarı tanınmıyor: {name}") from error


def _to_article(entry: Any, custom_images: Mapping[str, str], time_zone: tzinfo | None) -> ParsedArticle | None:
    """feedparser'ın verdiği haberi ortak yapıya çevirir; zorunlu bir alan eksikse None döner."""
    url = _text(entry.get("link"))
    # Kimlik vermeyen kaynaklarda haberin adresi kimlik sayılır.
    external_id = _text(entry.get("id")) or url
    title = to_plain_text(_text(entry.get("title")) or "")
    published_at = _published_at(entry, time_zone)
    if url is None or external_id is None or not is_http_url(url) or not title or published_at is None:
        return None

    raw_content = _first_content(entry)
    cleaned = clean_content(raw_content, base_url=url) if raw_content else None
    summary = _READ_MORE_SUFFIX.sub("", to_plain_text(_text(entry.get("summary")) or ""))

    return ParsedArticle(
        external_id=external_id,
        url=url,
        normalized_url=normalize_url(url),
        title=title,
        summary=summary or None,
        content=(cleaned.html or None) if cleaned else None,
        author=_text(entry.get("author")),
        published_at=published_at,
        item_type=ItemType.VIDEO if urlsplit(url).path.startswith(_VIDEO_PATH_PREFIX) else ItemType.ARTICLE,
        image_urls=_image_urls(entry, custom_images.get(external_id), cleaned.image_urls if cleaned else ()),
        source_categories=_source_categories(entry, url),
    )


def _published_at(entry: Any, time_zone: tzinfo | None) -> datetime | None:
    # feedparser tarihi hangi saat diliminde gelirse gelsin UTC'ye çevirip verir (FG-VT-08);
    # burada yalnızca Python tarihine dönüştürülür. Yayın tarihi yoksa güncellenme tarihi kullanılır.
    parsed_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed_time is None:
        return None
    year, month, day, hour, minute, second = parsed_time[:6]
    published_at = datetime(year, month, day, hour, minute, second, tzinfo=UTC)
    if time_zone is None:
        return published_at
    # feedparser'ın UTC'ye çevirdiği değer yazan saat dilimine göre hesaplanmıştır; burada saat,
    # beslemede yazıldığı haliyle yeniden okunur ve kaynağın gerçek saat dilimiyle yorumlanır.
    written = _written_clock_time(entry.get("published") or entry.get("updated"))
    if written is None:
        return published_at
    return written.replace(tzinfo=time_zone).astimezone(UTC)


def _written_clock_time(value: Any) -> datetime | None:
    """Tarihin beslemede yazdığı gün ve saat; yanındaki saat dilimi bilgisi atılmış olarak.

    RSS tarihleri e-posta biçimindedir (`Fri, 13 Nov 2026 16:28:48 GMT`), Atom tarihleri ISO 8601
    (`2026-11-13T16:28:48Z`). İkisi de okunamazsa None döner; o zaman feedparser'ın değeri kullanılır.
    """
    if not isinstance(value, str):
        return None
    try:
        return parsedate_to_datetime(value).replace(tzinfo=None)
    except TypeError, ValueError:
        pass
    try:
        return datetime.fromisoformat(value).replace(tzinfo=None)
    except ValueError:
        return None


def _first_content(entry: Any) -> str | None:
    for content in entry.get("content") or []:
        value = _text(content.get("value"))
        if value is not None:
            return value
    return None


def _image_urls(entry: Any, custom_image: str | None, content_images: tuple[str, ...]) -> tuple[str, ...]:
    """Haberin görsellerini öncelik sırasıyla döner; ilki ana görseldir.

    Sıra: kaynağa özgü alan (alan eşlemesi), <enclosure>, içerikteki <img> etiketleri. Kaynağa özgü
    alandan görsel geldiyse <enclosure> okunmaz: Akşam <enclosure>'da bozuk adres verir.
    Bunlar yoksa yedekler sırayla denenir ve ilk bulunan tek görsel kullanılır:
    - `media:content`: bazı kaynaklarda (Global Voices) küçük bir önizleme resmidir; büyük görsel içeriktedir.
    - Özetteki <img>: Milliyet ve Karar görseli yalnızca özette verir.
    - `media:thumbnail`: BBC Türkçe görseli yalnızca küçük bir önizleme resmi olarak verir.
    """
    candidates: list[str] = []
    if custom_image is not None:
        # Kaynağa özgü alan <enclosure>'ın yerine geçer. Akşam'da ikisi aynı görseli gösterir ama
        # <enclosure>'daki adresin eğik çizgisi eksiktir (imgsdisk2026/...); ikinci görsel olarak
        # kaydedilse her haber için siteye 404 dönecek bir istek daha gider.
        candidates.append(custom_image)
    else:
        for enclosure in entry.get("enclosures") or []:
            url = _text(enclosure.get("href"))
            # <enclosure> ses veya video da taşıyabilir; yalnızca görsel türündekiler alınır.
            if url is not None and _is_image_type(enclosure.get("type")):
                candidates.append(url)
    candidates.extend(content_images)

    # Aynı görsel farklı boyut parametreleriyle tekrar gelebilir (NTV: ?width=930&format=webp);
    # parametresiz adresi aynı olanlardan ilki tutulur.
    unique: dict[str, str] = {}
    for url in candidates:
        if is_http_url(url):
            unique.setdefault(_without_query(url), url)
    if unique:
        return tuple(unique.values())

    for media in entry.get("media_content") or []:
        url = _text(media.get("url"))
        is_image = media.get("medium") == "image" or _is_image_type(media.get("type"))
        if url is not None and is_image and is_http_url(url):
            return (url,)

    summary = _text(entry.get("summary"))
    if summary is not None:
        for url in clean_content(summary).image_urls:
            if is_http_url(url):
                return (url,)

    for thumbnail in entry.get("media_thumbnail") or []:
        url = _text(thumbnail.get("url"))
        if url is not None and is_http_url(url):
            return (url,)
    return ()


def _source_categories(entry: Any, url: str) -> tuple[str, ...]:
    """Haberin kaynaktaki kategori değerlerini döner; ortak kategoriye çevirmek eşleme tablosunun işidir.

    Kategori etiketi veren kaynaklarda (NTV, Global Voices) etiketler kullanılır. Etiket vermeyen
    kaynaklarda (TRT, CNN Türk) kategori adrestedir: adresin klasör kısımları aday olarak döner
    (`/haber/ekonomi/baslik-1.html` → `haber`, `ekonomi`). Eşleme tablosunda bulunmayan aday
    (`haber`, `video`) kendiliğinden elenir.
    """
    terms = (_text(tag.get("term")) for tag in entry.get("tags") or [])
    # dict.fromkeys: sırayı koruyarak tekrarları atar.
    tags = tuple(dict.fromkeys(term for term in terms if term is not None))
    if tags:
        return tags
    segments = [segment for segment in urlsplit(url).path.split("/") if segment]
    # Son parça haberin kendi adıdır, kategori değildir.
    return tuple(dict.fromkeys(segments[:-1]))


def _read_custom_field(body: bytes, element_name: str) -> dict[str, str]:
    """Her haberin içindeki `element_name` adlı etiketin değerini, haber kimliğine göre döner.

    feedparser standart dışı etiketleri atar (CNN Türk'ün haber içindeki <image> etiketi);
    bu yüzden alan eşlemesinde tanımlı etiket XML'den ayrıca okunur.
    """
    try:
        # Python'un XML okuyucusu dış varlıkları yüklemez; iç içe varlıklarla belleği doldurma
        # saldırısına karşı koruma da kullanılan expat sürümünde vardır (2.4.1 ve sonrası).
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError:
        # feedparser bozuk XML'i de okuyabilir; o durumda haberler özel alan olmadan döner.
        log.warning("Besleme geçerli bir XML olmadığı için <%s> alanı okunamadı", element_name)
        return {}

    values: dict[str, str] = {}
    for item in root.iter():
        if _local_name(item.tag) not in _ITEM_TAGS:
            continue
        children: dict[str, str] = {}
        for child in item:
            text = _text(child.text)
            if text is not None:
                # Aynı adlı etiketlerden ilki: <link> ile içi boş <atom:link> birlikte bulunabilir.
                children.setdefault(_local_name(child.tag), text)
        # feedparser'ın kimlik seçimiyle aynı sıra: RSS'te guid, Atom'da id, yoksa adres.
        key = children.get("guid") or children.get("id") or children.get("link")
        value = children.get(element_name)
        if key is not None and value is not None:
            values[key] = value
    return values


def _local_name(tag: str) -> str:
    """`{http://www.w3.org/2005/Atom}entry` gibi ad alanlı etiket adından yalın adı verir."""
    return tag.rsplit("}", 1)[-1]


def _without_query(url: str) -> str:
    return urlsplit(url)._replace(query="", fragment="").geturl()


def _is_image_type(content_type: object) -> bool:
    return isinstance(content_type, str) and content_type.startswith(_IMAGE_TYPE_PREFIX)


def _text(value: object) -> str | None:
    """Değer boş olmayan bir metinse çevresindeki boşluklar atılmış halini, değilse None döner."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
