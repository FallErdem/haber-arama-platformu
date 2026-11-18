import logging
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest

from news_worker.feed_reader import IMAGE_FIELD, FeedParseError, FeedReader, FeedReadResult
from news_worker.parsed_article import ItemType

FIXTURES = Path(__file__).parent / "fixtures" / "feeds"

CNNTURK_FIELD_MAPPING = {IMAGE_FIELD: "image"}

VALID_ITEM = """
    <item>
      <guid>haber-1</guid>
      <title>Geçerli haber</title>
      <link>https://example.test/haber-1</link>
      <pubDate>Fri, 13 Nov 2026 16:40:00 +0300</pubDate>
      {extra}
    </item>
"""


def read_fixture(name: str, field_mapping: dict[str, str] | None = None) -> FeedReadResult:
    return FeedReader().read((FIXTURES / name).read_bytes(), field_mapping)


def rss(*items: str) -> bytes:
    """Elle yazılmış haberlerden küçük bir RSS beslemesi kurar."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel><title>Örnek</title>'
        + "".join(items)
        + "</channel></rss>"
    ).encode()


def test_rss_item_is_converted_to_common_structure() -> None:
    """TRT (RSS): haberin alanları ortak yapıya doğru yerleşir."""
    result = read_fixture("trt-gundem.xml")

    assert len(result.articles) == 3
    assert result.skipped_count == 0
    article = result.articles[0]
    url = "https://www.trthaber.com/haber/gundem/cumhurbaskani-erdoganin-katar-emiri-al-sani-ile-gorusuyor-963198.html"
    assert article.external_id == url
    assert article.url == url
    assert article.normalized_url == url
    assert article.title == "Cumhurbaşkanı Erdoğan'ın, Katar Emiri Al Sani ile görüşüyor"
    assert article.author == "TRT Haber"
    assert article.item_type is ItemType.ARTICLE


def test_url_folders_are_category_candidates_when_there_are_no_category_tags() -> None:
    """TRT ve CNN Türk kategori etiketi vermez; adresin klasör kısımları aday olur, haberin adı olmaz."""
    trt_article = read_fixture("trt-gundem.xml").articles[0]
    cnnturk_articles = read_fixture("cnnturk-all.xml").articles

    assert trt_article.source_categories == ("haber", "gundem")
    assert [article.source_categories for article in cnnturk_articles] == [
        ("video", "dunya"),
        ("ekonomi",),
        ("yerel-haberler", "usak"),
    ]


def test_category_tags_are_preferred_over_url_folders() -> None:
    """Kategori etiketi veren kaynakta (NTV) adres kullanılmaz."""
    article = read_fixture("ntv-turkiye.xml").articles[0]

    assert "/turkiye/" in article.url
    assert article.source_categories == ("Türkiye",)


def test_publication_time_is_converted_to_utc() -> None:
    """TRT tarihi `+0300` ile verir; 16:40 Türkiye saati 13:40 UTC'dir (FG-VT-08)."""
    article = read_fixture("trt-gundem.xml").articles[0]

    assert article.published_at == datetime(2026, 11, 13, 13, 40, tzinfo=UTC)


def test_old_publication_dates_are_kept() -> None:
    """TRT'nin `koronavirus` beslemesi 2023 tarihli haberler verir; tarih olduğu gibi korunur."""
    articles = read_fixture("trt-koronavirus.xml").articles

    assert [article.published_at.year for article in articles] == [2023, 2023]


def test_declared_time_zone_is_trusted_without_feed_time_zone() -> None:
    """Kaynağın saat dilimi ayarı yoksa beslemede yazan saat dilimine güvenilir."""
    article = read_fixture("cnnturk-turkiye.xml").articles[0]

    assert article.published_at == datetime(2026, 11, 13, 16, 28, 48, tzinfo=UTC)


def test_feed_time_zone_corrects_local_time_labelled_as_gmt() -> None:
    """CNN Türk saati Türkiye saatiyle yazıp yanına "GMT" koyar: `16:28:48 GMT` gerçekte 13:28:48 UTC'dir.

    Kaynağın saat dilimi ayarı verildiğinde beslemede yazan saat o saat diliminde okunur.
    """
    body = (FIXTURES / "cnnturk-turkiye.xml").read_bytes()

    article = FeedReader().read(body, CNNTURK_FIELD_MAPPING, feed_time_zone="Europe/Istanbul").articles[0]

    assert article.published_at == datetime(2026, 11, 13, 13, 28, 48, tzinfo=UTC)


@pytest.mark.parametrize(
    "pub_date",
    ["Fri, 13 Nov 2026 16:40:00 +0300", "Fri, 13 Nov 2026 16:40:00 +0000", "Fri, 13 Nov 2026 16:40:00 GMT"],
)
def test_feed_time_zone_ignores_the_declared_offset(pub_date: str) -> None:
    """Ayar verildiğinde yazan saat esas alınır; yanındaki saat dilimi ne olursa olsun sonuç aynıdır."""
    body = rss(VALID_ITEM.format(extra="").replace("Fri, 13 Nov 2026 16:40:00 +0300", pub_date))

    article = FeedReader().read(body, feed_time_zone="Europe/Istanbul").articles[0]

    assert article.published_at == datetime(2026, 11, 13, 13, 40, tzinfo=UTC)


def test_feed_time_zone_applies_to_atom_dates() -> None:
    """Atom beslemelerinde tarih ISO 8601 biçimindedir; ayar aynı şekilde uygulanır."""
    body = (
        '<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom"><title>Örnek</title>'
        "<entry><id>haber-1</id><title>Atom haberi</title>"
        '<link href="https://example.test/haber-1"/><updated>2026-11-13T16:40:00Z</updated></entry></feed>'
    ).encode()

    article = FeedReader().read(body, feed_time_zone="Europe/Istanbul").articles[0]

    assert article.published_at == datetime(2026, 11, 13, 13, 40, tzinfo=UTC)


def test_unknown_feed_time_zone_raises_parse_error() -> None:
    """Ayardaki saat dilimi adı tanınmıyorsa (yazım hatası) okuma başarısız sayılır ve neden görünür."""
    with pytest.raises(FeedParseError, match="Avrupa/Istanbul"):
        FeedReader().read(rss(VALID_ITEM.format(extra="")), feed_time_zone="Avrupa/Istanbul")


def test_summary_is_plain_text_without_leading_image() -> None:
    """TRT özeti <img> ile başlar; özette yalnızca cümle kalır, görsel ana görsel olur."""
    article = read_fixture("trt-gundem.xml").articles[0]

    assert article.summary is not None
    assert article.summary.startswith("Cumhurbaşkanı Recep Tayyip Erdoğan")
    assert "<" not in article.summary
    assert article.image_urls == (
        "https://trthaberstatic.cdn.wp.trt.com.tr/resimler/2502000/erdogan-al-sani-2503504.jpg",
    )


def test_atom_entry_is_converted_to_common_structure() -> None:
    """NTV (Atom): aynı okuyucu Atom beslemesini de okur; kategori ve yazar gelir."""
    result = read_fixture("ntv-turkiye.xml")

    assert len(result.articles) == 2
    article = result.articles[0]
    assert article.external_id == article.url
    assert article.url.startswith("https://www.ntv.com.tr/turkiye/malatyanin-deprem-sonrasi-donusumu")
    assert article.title == "Malatya'nın deprem sonrası dönüşümü COP31'de gündeme geldi"
    assert article.author == "NTV"
    assert article.source_categories == ("Türkiye",)
    assert article.published_at == datetime(2026, 11, 13, 13, 55, 6, tzinfo=UTC)


def test_content_is_cleaned_and_its_images_are_moved_to_image_list() -> None:
    """NTV içeriğinde <img> kalmaz; görseller listede, ana görsel (<enclosure>) başta yer alır."""
    article = read_fixture("ntv-turkiye.xml").articles[0]

    assert article.content is not None
    assert "<img" not in article.content
    assert "<p>" in article.content
    assert article.image_urls == (
        "https://images.ntv.com.tr/images/malatya1-502850.jpeg",
        "https://images.ntv.com.tr/images/malatya2-238578.jpeg",
    )


def test_same_image_with_size_parameters_is_listed_once() -> None:
    """NTV ana görseli içerikte `?width=930&format=webp` ekiyle yeniden verir; tek görsel sayılır."""
    article = read_fixture("ntv-turkiye.xml").articles[1]

    assert article.image_urls == ("https://images.ntv.com.tr/images/Ekrangörüntüsü2026-11-13161543-771614.png",)


def test_empty_feed_is_not_an_error() -> None:
    """NTV'nin `galeri` beslemesi haber içermeden döner; bu bir hata değildir."""
    result = read_fixture("ntv-galeri.xml")

    assert result.articles == ()
    assert result.skipped_count == 0


def test_custom_image_field_is_read_with_field_mapping() -> None:
    """CNN Türk görseli haberin içindeki <image> etiketinde verir; alan eşlemesiyle okunur."""
    article = read_fixture("cnnturk-turkiye.xml", CNNTURK_FIELD_MAPPING).articles[0]

    assert article.image_urls == ("https://image.cnnturk.com/i/cnnturk/75/720x490/6af70820ae7031b6f4159010.jpg",)


def test_custom_image_field_is_ignored_without_field_mapping() -> None:
    """Alan eşlemesi tanımlı değilse standart dışı <image> etiketi okunmaz."""
    articles = read_fixture("cnnturk-turkiye.xml").articles

    assert [article.image_urls for article in articles] == [(), (), ()]


def test_item_without_custom_image_has_no_image() -> None:
    """Alan eşlemesi olsa da <image> etiketi bulunmayan haberin görseli yoktur."""
    article = read_fixture("cnnturk-all.xml", CNNTURK_FIELD_MAPPING).articles[2]

    assert "/yerel-haberler/" in article.url
    assert article.image_urls == ()


def test_external_id_is_guid_even_when_it_is_not_the_url() -> None:
    """CNN Türk'ün kimliği adres değil, kendi iç kimliğidir; içerik ve yazar gelmez."""
    article = read_fixture("cnnturk-turkiye.xml").articles[0]

    assert article.external_id == "6af70729ae7031b6f4158ffe"
    assert article.url.startswith("https://www.cnnturk.com/turkiye/")
    assert article.content is None
    assert article.author is None


def test_url_under_video_path_is_a_video() -> None:
    """Adresi `/video/` ile başlayan haber video sayılır; diğerleri haberdir."""
    articles = read_fixture("cnnturk-all.xml").articles

    assert articles[0].url.startswith("https://www.cnnturk.com/video/")
    assert [article.item_type for article in articles] == [ItemType.VIDEO, ItemType.ARTICLE, ItemType.ARTICLE]


def test_feed_with_many_categories_and_separate_guid() -> None:
    """Global Voices: kimlik ile adres farklıdır; adresin sonundaki eğik çizgi normalleştirmede atılır."""
    article = read_fixture("globalvoices.xml").articles[0]

    assert article.external_id == "https://globalvoices.org/?p=859567"
    assert article.url == (
        "https://globalvoices.org/2026/11/13/how-medical-neglect-killed-alfredo-diaz-in-a-venezuelan-cell/"
    )
    assert article.normalized_url == article.url.rstrip("/")
    assert article.author == "Luis Carlos Diaz"
    assert article.source_categories == (
        "English",
        "Feature",
        "Human Rights",
        "Latin America",
        "Venezuela",
        "Weblog",
    )


def test_content_image_is_preferred_over_media_thumbnail() -> None:
    """Global Voices'ta `media:content` küçük önizlemedir; içerikteki büyük görsel kullanılır."""
    article = read_fixture("globalvoices.xml").articles[0]

    assert article.image_urls == ("https://globalvoices.org/wp-content/uploads/2026/10/Alfreditopiece-1024x768-1.webp",)


def test_real_content_with_script_is_stored_without_it() -> None:
    """Global Voices'ın betik etiketi içeren haberi temizlenmiş olarak gelir (FOG-16)."""
    raw = (FIXTURES / "globalvoices.xml").read_text(encoding="utf-8")
    assert "<script" in raw

    articles = read_fixture("globalvoices.xml").articles

    assert all(article.content is not None and "<script" not in article.content for article in articles)


def test_media_content_is_used_when_there_is_no_other_image() -> None:
    """Başka görsel yoksa `media:content` ana görsel olur."""
    body = rss(
        VALID_ITEM.format(extra='<media:content url="https://example.test/onizleme.jpg" medium="image"/>'),
    )

    article = FeedReader().read(body).articles[0]

    assert article.image_urls == ("https://example.test/onizleme.jpg",)


def test_non_image_enclosure_is_not_an_image() -> None:
    """<enclosure> ses dosyası da taşıyabilir; görsel türünde olmayan alınmaz."""
    body = rss(
        VALID_ITEM.format(extra='<enclosure url="https://example.test/bolum.mp3" type="audio/mpeg" length="1"/>'),
    )

    article = FeedReader().read(body).articles[0]

    assert article.image_urls == ()


def test_title_markup_is_removed() -> None:
    """Başlıktaki HTML atılır; başlık düz metindir."""
    body = rss(
        "<item><guid>haber-2</guid><title><![CDATA[<b>Önemli</b> gelişme <script>alert(1)</script>]]></title>"
        "<link>https://example.test/haber-2</link><pubDate>Fri, 13 Nov 2026 16:40:00 GMT</pubDate></item>"
    )

    article = FeedReader().read(body).articles[0]

    assert article.title == "Önemli gelişme"


def test_link_is_used_as_external_id_when_guid_is_missing() -> None:
    """Kimlik vermeyen haberde adres kimlik sayılır."""
    body = rss(
        "<item><title>Kimliksiz haber</title><link>https://example.test/haber-3</link>"
        "<pubDate>Fri, 13 Nov 2026 16:40:00 GMT</pubDate></item>"
    )

    article = FeedReader().read(body).articles[0]

    assert article.external_id == "https://example.test/haber-3"


def test_items_missing_required_fields_are_skipped_and_counted(caplog: pytest.LogCaptureFixture) -> None:
    """Başlığı, adresi veya tarihi olmayan haber atlanır; besleme başarısız sayılmaz, sayı loga yazılır."""
    date = "<pubDate>Fri, 13 Nov 2026 16:40:00 GMT</pubDate>"
    body = rss(
        VALID_ITEM.format(extra=""),
        f"<item><guid>a</guid><link>https://example.test/a</link>{date}</item>",
        f"<item><guid>b</guid><title>Adressiz</title>{date}</item>",
        "<item><guid>c</guid><title>Tarihsiz</title><link>https://example.test/c</link></item>",
        f"<item><guid>d</guid><title>Zararlı adres</title><link>javascript:alert(1)</link>{date}</item>",
    )

    with caplog.at_level(logging.WARNING):
        result = FeedReader().read(body)

    assert [article.external_id for article in result.articles] == ["haber-1"]
    assert result.skipped_count == 4
    assert "4 haber atlandı" in caplog.text


@pytest.mark.parametrize(
    "body",
    [b"", b"besleme degil", b"<html><body><h1>403 Forbidden</h1></body></html>"],
    ids=["empty", "plain-text", "html-error-page"],
)
def test_unrecognized_content_raises_parse_error(body: bytes) -> None:
    """Besleme yerine boş yanıt, düz metin veya bir hata sayfası gelirse okuma hata verir."""
    with pytest.raises(FeedParseError):
        FeedReader().read(body)


def test_body_is_never_treated_as_a_file_path(tmp_path: Path) -> None:
    """İçerik bir dosya yolu gibi görünse de o dosya açılmaz; yalnızca gelen metin okunur."""
    feed_file = tmp_path / "feed.xml"
    feed_file.write_bytes(rss(VALID_ITEM.format(extra="")))

    with pytest.raises(FeedParseError):
        FeedReader().read(str(feed_file).encode())


def test_malformed_xml_is_read_without_custom_fields(caplog: pytest.LogCaptureFixture) -> None:
    """Etiketi kapatılmamış beslemede haberler yine okunur; yalnızca özel alan okunamaz."""
    body = (
        b'<rss version="2.0"><channel><item><guid>haber-1</guid><title>Bozuk besleme</title>'
        b"<link>https://example.test/haber-1</link><pubDate>Fri, 13 Nov 2026 16:40:00 GMT</pubDate>"
        b"<image>https://example.test/gorsel.jpg</image></channel>"
    )

    with caplog.at_level(logging.WARNING):
        result = FeedReader().read(body, CNNTURK_FIELD_MAPPING)

    assert [article.title for article in result.articles] == ["Bozuk besleme"]
    assert result.articles[0].image_urls == ()
    assert "<image> alanı okunamadı" in caplog.text


def test_seeded_field_mapping_reads_cnnturk_images(admin: psycopg.Connection) -> None:
    """Veritabanındaki CNN Türk alan eşlemesi (V12) okuyucuya verildiğinde görseller bulunur."""
    row = admin.execute("SELECT field_mapping FROM sources WHERE code = 'CNNTURK'").fetchone()
    assert row is not None
    field_mapping: dict[str, str] = row[0]

    articles = read_fixture("cnnturk-turkiye.xml", field_mapping).articles

    assert all(len(article.image_urls) == 1 for article in articles)


def test_other_sources_have_no_field_mapping(admin: psycopg.Connection) -> None:
    """Görseli standart alanlarda veren kaynakların alan eşlemesi boştur."""
    rows = admin.execute("SELECT code FROM sources WHERE field_mapping IS NOT NULL ORDER BY code").fetchall()

    assert rows == [("CNNTURK",)]


def test_only_cnnturk_has_a_feed_time_zone(admin: psycopg.Connection) -> None:
    """Saat dilimini doğru yazan kaynakların ayarı boştur; yalnızca CNN Türk'ünki doludur (V15)."""
    rows = admin.execute("SELECT code, feed_time_zone FROM sources WHERE feed_time_zone IS NOT NULL").fetchall()

    assert rows == [("CNNTURK", "Europe/Istanbul")]
