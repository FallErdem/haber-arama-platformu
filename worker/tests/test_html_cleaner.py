from pathlib import Path

import feedparser

from news_worker.html_cleaner import clean_content, to_plain_text

FIXTURES = Path(__file__).parent / "fixtures" / "feeds"

# Elle yazılmış zararlı içerik: betik, olay öznitelikleri, zararlı bağlantı, gömülü sayfa ve stil.
MALICIOUS_HTML = (
    '<p onclick="steal()">Merhaba <script>alert("xss")</script>'
    '<a href="javascript:alert(1)">tuzak</a> '
    '<a href="https://example.test/haber">bağlantı</a>'
    '<img src="https://example.test/gorsel.jpg" onerror="steal()">'
    '<iframe src="https://example.test/gomulu"></iframe>'
    "<style>p { display: none }</style></p>"
)


def _raw_item_text(fixture_name: str, field: str, item_index: int = 0) -> str:
    """Örnek dosyadaki bir haberin alanını, feedparser'ın kendi temizliği kapatılarak okur.

    Böylece testler bizim temizleyicimizi kaynağın gönderdiği ham HTML ile sınar.
    """
    parsed = feedparser.parse((FIXTURES / fixture_name).read_bytes(), sanitize_html=False)
    entry = parsed.entries[item_index]
    value = entry.content[0].value if field == "content" else entry[field]
    assert isinstance(value, str)
    return value


def test_script_and_its_code_are_removed() -> None:
    """Betik etiketi içindeki kodla birlikte gider."""
    cleaned = clean_content(MALICIOUS_HTML)

    assert "script" not in cleaned.html
    assert "alert" not in cleaned.html


def test_event_attributes_are_removed() -> None:
    """`onclick` ve `onerror` gibi olay öznitelikleri kalmaz."""
    cleaned = clean_content(MALICIOUS_HTML)

    assert "onclick" not in cleaned.html
    assert "onerror" not in cleaned.html
    assert "steal" not in cleaned.html


def test_javascript_link_loses_its_address_but_safe_link_is_kept() -> None:
    """`javascript:` adresi atılır; `https` bağlantısı korunur."""
    cleaned = clean_content(MALICIOUS_HTML)

    assert "javascript:" not in cleaned.html
    assert 'href="https://example.test/haber"' in cleaned.html


def test_iframe_and_style_are_removed() -> None:
    """Gömülü sayfa ve stil etiketleri kalmaz."""
    cleaned = clean_content(MALICIOUS_HTML)

    assert "iframe" not in cleaned.html
    assert "style" not in cleaned.html
    assert "display" not in cleaned.html


def test_harmless_text_and_tags_are_kept() -> None:
    """Zararsız etiketler ve yazı yerinde kalır."""
    cleaned = clean_content("<p>Birinci <strong>önemli</strong> cümle.</p>")

    assert cleaned.html == "<p>Birinci <strong>önemli</strong> cümle.</p>"
    assert cleaned.image_urls == ()


def test_images_are_removed_from_content_and_returned_separately() -> None:
    """<img> içerikten çıkar; adresi ayrı listede döner."""
    cleaned = clean_content(MALICIOUS_HTML)

    assert "<img" not in cleaned.html
    assert cleaned.image_urls == ("https://example.test/gorsel.jpg",)


def test_image_urls_keep_order_and_drop_duplicates() -> None:
    """Görseller içerikteki sırasıyla döner; aynı adres bir kez yer alır."""
    cleaned = clean_content(
        '<img src="https://example.test/b.jpg"><p>yazı</p>'
        '<img src="https://example.test/a.jpg"><img src="https://example.test/b.jpg">'
    )

    assert cleaned.image_urls == ("https://example.test/b.jpg", "https://example.test/a.jpg")


def test_only_http_and_https_image_urls_are_collected() -> None:
    """İndirilemeyecek adresler (`data:`, `javascript:`, göreli yol, boş) görsel sayılmaz."""
    cleaned = clean_content(
        '<img src="data:image/png;base64,AAAA"><img src="javascript:alert(1)">'
        '<img src="/images/a.jpg"><img src=""><img alt="adressiz">'
        '<img src=" HTTPS://example.test/ok.jpg ">'
    )

    assert cleaned.image_urls == ("HTTPS://example.test/ok.jpg",)


def test_real_content_with_script_is_cleaned() -> None:
    """Global Voices içeriğindeki gerçek betik etiketleri temizlenir; paragraflar korunur."""
    # Örnek dosyadaki ikinci haber, gömülü bir paylaşım nedeniyle iki betik etiketi içerir.
    raw = _raw_item_text("globalvoices.xml", "content", item_index=1)
    assert "<script" in raw

    cleaned = clean_content(raw)

    assert "<script" not in cleaned.html
    assert "<p>" in cleaned.html


def test_real_content_images_are_extracted() -> None:
    """NTV içeriğindeki görseller çıkarılır; görselin altındaki açıklama yazısı içerikte kalır."""
    cleaned = clean_content(_raw_item_text("ntv-turkiye.xml", "content"))

    assert "<img" not in cleaned.html
    assert cleaned.image_urls == (
        "https://images.ntv.com.tr/images/malatya1-502850.jpeg?width=930&format=webp",
        "https://images.ntv.com.tr/images/malatya2-238578.jpeg",
    )
    assert "<figcaption>" in cleaned.html


def test_plain_text_drops_leading_image_of_real_summary() -> None:
    """TRT özeti <img> ile başlar; düz metinde yalnızca cümle kalır."""
    raw = _raw_item_text("trt-gundem.xml", "summary")
    assert raw.startswith("<img")

    text = to_plain_text(raw)

    assert text.startswith("Cumhurbaşkanı Recep Tayyip Erdoğan")
    assert "<" not in text


def test_plain_text_does_not_contain_script_code() -> None:
    """Betiğin kodu düz metne karışmaz."""
    assert to_plain_text(MALICIOUS_HTML) == "Merhaba tuzak bağlantı"


def test_plain_text_separates_paragraphs_but_not_inline_tags() -> None:
    """Paragraflar arasına boşluk girer; kelimenin içindeki biçim etiketi kelimeyi bölmez."""
    assert to_plain_text("<p>Birinci.</p><p>İkin<b>ci</b>.</p>") == "Birinci. İkinci."


def test_plain_text_decodes_entities_and_collapses_whitespace() -> None:
    """`&amp;` gibi kodlar çözülür; art arda boşluklar ve satır sonları tek boşluğa iner."""
    assert to_plain_text("  Ekonomi &amp; Finans\n\n  haberleri&nbsp;burada ") == "Ekonomi & Finans haberleri burada"


def test_embedded_editor_blocks_are_removed_from_text() -> None:
    """Milliyet'in editörünün metne gömdüğü kutular (görsel yer tutucusu, ilgili haber) yazıya karışmaz."""
    html = (
        "<p>Birinci.</p>"
        '<section class="insert insert-controls mceNonEditable" data-controls="%5B%5D" data-type="Control">'
        "Infografik Görsel (Quality Image)</section>"
        "<p>İkinci.</p>"
        '<section class="insert insert-contents mceNonEditable" data-type="Content">Başka bir haberin başlığı</section>'
    )

    assert to_plain_text(html) == "Birinci. İkinci."
    assert clean_content(html).html == "<p>Birinci.</p><p>İkinci.</p>"


def test_related_news_box_and_its_images_are_removed_from_content() -> None:
    """BirGün'ün "İlgili haberler" kutusundaki başlık ve küçük resimler başka haberlerindir; alınmaz."""
    html = (
        "<p>Haberin metni.</p>"
        '<aside class="inline-related font-sans" aria-label="İlgili haberler"><article>'
        '<a href="/haber/baska-haber"><img src="https://static.example.test/list-haber/baska.jpg"></a>'
        '<h3><a href="/haber/baska-haber">Başka haber</a></h3>'
        "</article></aside>"
    )

    cleaned = clean_content(html)

    assert cleaned.html == "<p>Haberin metni.</p>"
    assert cleaned.image_urls == ()


def test_aside_without_related_news_class_is_kept() -> None:
    """Global Voices <aside> içinde haberin kendi metnini verir; yalnızca işaretli kutular atılır."""
    cleaned = clean_content("<p>Giriş.</p><aside><div>Haberin bir parçası.</div></aside>")

    assert "Haberin bir parçası." in cleaned.html


def test_same_tag_nested_in_removed_block_does_not_end_it_early() -> None:
    """Kutunun içindeki aynı adlı etiketin kapanışı kutuyu bitirmez; kutu kendi kapanışına kadar atılır."""
    html = '<section class="mceNonEditable"><section>iç</section>hâlâ kutu</section><p>Sonra.</p>'

    assert to_plain_text(html) == "Sonra."


def test_unclosed_block_is_kept() -> None:
    """Kapanmayan kutu atılmaz: yazının geri kalanını kaybetmektense kutunun yazısı kalır."""
    assert to_plain_text('<p>Önce.</p><section class="mceNonEditable">kutu') == "Önce. kutu"


def test_relative_links_are_resolved_against_the_article_address() -> None:
    """NTV ve BirGün metin içinde göreli bağlantı verir; bizim sitemizde açılmasınlar diye tam adrese çevrilir."""
    cleaned = clean_content(
        '<p><a href="/sporskor/diger-haber">Wenger</a></p>', base_url="https://www.ntv.com.tr/sporskor/bu-haber"
    )

    assert 'href="https://www.ntv.com.tr/sporskor/diger-haber"' in cleaned.html


def test_empty_input_gives_empty_result() -> None:
    """Boş veya yalnızca boşluk içeren girdi hata vermez."""
    assert clean_content("   ") == clean_content("")
    assert clean_content("").html == ""
    assert clean_content("").image_urls == ()
    assert to_plain_text("  \n ") == ""
