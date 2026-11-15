import pytest

from news_worker.url_normalizer import normalize_url


def test_plain_url_is_unchanged() -> None:
    """Normalleştirilecek bir şeyi olmayan adres aynen kalır."""
    url = "https://www.trthaber.com/haber/gundem/ornek-haber-963198.html"

    assert normalize_url(url) == url


def test_different_articles_in_same_section_stay_different() -> None:
    """Yol kısaltılmaz: aynı bölümdeki iki haber, ekleri atıldıktan sonra da ayrı adreslerdir."""
    first = normalize_url("https://www.ntv.com.tr/turkiye/deprem-haberi-1750633/?utm_source=rss#yorumlar")
    second = normalize_url("https://www.ntv.com.tr/turkiye/malatya-haberi-1750747/?utm_source=rss#yorumlar")

    assert first == "https://www.ntv.com.tr/turkiye/deprem-haberi-1750633"
    assert second == "https://www.ntv.com.tr/turkiye/malatya-haberi-1750747"


def test_scheme_and_host_are_lowercased_but_path_is_not() -> None:
    """Şema ve alan adı küçük harfe çevrilir; yol büyük/küçük harfe duyarlı olduğu için dokunulmaz."""
    assert normalize_url("HTTPS://WWW.NTV.com.tr/Turkiye/Haber-1") == "https://www.ntv.com.tr/Turkiye/Haber-1"


def test_fragment_is_removed() -> None:
    """`#` ile başlayan kısım atılır."""
    assert normalize_url("https://globalvoices.org/2026/11/13/story#comments") == (
        "https://globalvoices.org/2026/11/13/story"
    )


def test_trailing_slash_is_removed() -> None:
    """Sonunda eğik çizgi olan ve olmayan adres aynı habere iner."""
    assert normalize_url("https://globalvoices.org/2026/11/13/story/") == normalize_url(
        "https://globalvoices.org/2026/11/13/story"
    )


def test_tracking_parameters_are_removed() -> None:
    """`utm_` ile başlayan izleme parametreleri atılır."""
    url = "https://globalvoices.org/2026/11/13/story/?utm_source=rss&UTM_Medium=feed"

    assert normalize_url(url) == "https://globalvoices.org/2026/11/13/story"


def test_other_parameters_are_kept_in_order() -> None:
    """Haberi belirleyen parametreler korunur (Global Voices kimlikleri `?p=...` biçimindedir)."""
    assert normalize_url("https://globalvoices.org/?p=859567&utm_source=rss&x=1") == (
        "https://globalvoices.org?p=859567&x=1"
    )


@pytest.mark.parametrize(
    "url", ["  https://www.cnnturk.com/turkiye/haber-1  ", "\nhttps://www.cnnturk.com/turkiye/haber-1\n"]
)
def test_surrounding_whitespace_is_ignored(url: str) -> None:
    """Beslemelerde adresin çevresinde boşluk veya satır sonu bulunabilir."""
    assert normalize_url(url) == "https://www.cnnturk.com/turkiye/haber-1"
