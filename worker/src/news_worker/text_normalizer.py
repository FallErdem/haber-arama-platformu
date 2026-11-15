"""Metinlerin karşılaştırılabilir hale getirilmesi.

Python'un `str.lower()` fonksiyonu Türkçe kurallarını bilmez: "I" harfini "ı" yerine "i" yapar,
"İ" harfini ise "i" ve ayrı bir nokta işareti olmak üzere iki karaktere çevirir. Türkçe metinler
bu yüzden buradaki fonksiyonla küçük harfe çevrilir (kodlama standartları, 7. bölüm).
"""

_TURKISH = "tr"


def turkish_lower(text: str) -> str:
    """Türkçe kurallarıyla küçük harfe çevirir: "I" → "ı", "İ" → "i"."""
    # Önce iki özel harf elle çevrilir; geri kalan harflerde Türkçe ile genel kural aynıdır.
    return text.replace("İ", "i").replace("I", "ı").lower()


def normalize_category(value: str, language: str) -> str:
    """Kaynağın kategori değerini `category_mappings.source_category` ile karşılaştırılacak hale getirir.

    Baştaki ve sondaki boşluklar atılır, değer kaynağın dilinin kurallarıyla küçük harfe çevrilir.
    """
    stripped = value.strip()
    return turkish_lower(stripped) if language == _TURKISH else stripped.lower()
