import pytest

from news_worker.text_normalizer import normalize_category, turkish_lower


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("İSTANBUL", "istanbul"),
        ("IŞIK", "ışık"),
        ("Iğdır ve İzmir", "ığdır ve izmir"),
        ("ÇĞÖŞÜ", "çğöşü"),
        ("Spor&Skor", "spor&skor"),
        ("zaten küçük", "zaten küçük"),
        ("", ""),
    ],
)
def test_turkish_lower_follows_turkish_rules(text: str, expected: str) -> None:
    """ "I" harfi "ı", "İ" harfi "i" olur; diğer harfler genel kuralla çevrilir."""
    assert turkish_lower(text) == expected


def test_builtin_lower_is_wrong_for_turkish() -> None:
    """Bu fonksiyonun neden gerektiğini gösterir: Python'un kendi fonksiyonu iki harfi de yanlış çevirir."""
    assert "IŞIK".lower() == "işik"
    # "İ" tek harf yerine "i" ve ayrı bir nokta işareti (iki karakter) olur.
    assert len("İ".lower()) == 2

    assert turkish_lower("IŞIK") == "ışık"
    assert turkish_lower("İ") == "i"


def test_category_is_stripped_and_lowercased_with_turkish_rules() -> None:
    """Türkçe kaynağın kategori değeri Türkçe kurallarıyla küçük harfe çevrilir."""
    assert normalize_category("  Türkiye ", "tr") == "türkiye"
    assert normalize_category("EĞİTİM", "tr") == "eğitim"
    assert normalize_category("IRAK", "tr") == "ırak"


def test_english_category_is_lowercased_with_general_rules() -> None:
    """İngilizce kaynakta "I" harfi "i" olur; Türkçe kuralı uygulanmaz."""
    assert normalize_category(" Arts & Culture ", "en") == "arts & culture"
    assert normalize_category("INDIA", "en") == "india"
