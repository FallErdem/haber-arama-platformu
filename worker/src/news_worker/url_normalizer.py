"""Haber adreslerinin normalleştirilmesi (FG-VT-04).

Aynı haber farklı yazılmış adreslerle gelebilir (izleme parametresi, sondaki eğik çizgi).
Normalleştirilmiş adres `articles.normalized_url` sütununa yazılır ve tekrar kontrolünde kullanılır;
kullanıcıya gösterilen adres haberin özgün adresidir.
"""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Ziyaretin nereden geldiğini izlemek için eklenen parametreler; haberi değiştirmezler.
_TRACKING_PARAMETER_PREFIX = "utm_"

_HTTP_SCHEMES = frozenset({"http", "https"})


def is_http_url(url: str) -> bool:
    """Adres `http` veya `https` ile mi başlıyor? `data:`, `javascript:` ve göreli yollar elenir."""
    return urlsplit(url).scheme.lower() in _HTTP_SCHEMES


def normalize_url(url: str) -> str:
    """Adresi karşılaştırılabilir hale getirir. Yol kısaltılmaz; yalnızca haberi belirlemeyen ekler atılır.

    - Şema ve alan adı küçük harfe çevrilir (bu ikisi büyük/küçük harfe duyarsızdır; yol duyarlıdır).
    - `#` ile başlayan kısım atılır (sayfanın içindeki bir yeri gösterir, haberi değil).
    - `utm_` ile başlayan parametreler atılır; diğer parametreler sırasıyla korunur.
    - Yolun sonundaki eğik çizgi atılır.
    """
    parts = urlsplit(url.strip())
    kept_parameters = [
        (name, value)
        for name, value in parse_qsl(parts.query, keep_blank_values=True)
        if not name.lower().startswith(_TRACKING_PARAMETER_PREFIX)
    ]
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/"),
            urlencode(kept_parameters),
            "",
        )
    )
