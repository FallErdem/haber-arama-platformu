"""Görsellerin ortak biçime çevrilmesi: WebP, en uzun kenar en fazla 1600 piksel.

Kaynaklardan gelen görseller farklı türlerde (JPEG, PNG, WebP) ve çok farklı boyutlardadır; bazıları
45 megapiksellik fotoğraflardır. Arayüzde bir görsel en fazla ekran genişliğinde gösterildiğinden hepsi
aynı biçime ve makul bir boyuta getirilir; depolama ve sayfa yükleme süresi azalır.
"""

import io
from dataclasses import dataclass

from PIL import Image, ImageOps

from news_worker.image_downloader import NotAnImageError

OUTPUT_CONTENT_TYPE = "image/webp"
# En uzun kenarın üst sınırı; geniş bir ekranda tam genişlikte gösterim için yeterli.
MAX_DIMENSION = 1600
# 0–100; 80, gözle fark edilmeyen kayıpla dosyayı belirgin küçültür.
WEBP_QUALITY = 80
# 0 (hızlı) – 6 (en küçük dosya); 4, sıkıştırma süresiyle dosya boyutu arasında dengedir.
WEBP_METHOD = 4

_ALPHA_MODES = frozenset({"RGBA", "LA", "PA"})


@dataclass(frozen=True)
class ConvertedImage:
    body: bytes
    width: int
    height: int
    content_type: str = OUTPUT_CONTENT_TYPE


def convert_to_webp(body: bytes) -> ConvertedImage:
    """Görseli WebP'ye çevirir ve gerekirse küçültür. Görsel olarak açılamazsa `NotAnImageError` fırlatır.

    1. JPEG'ler baştan küçültülerek açılır (taslak kipi): 8256 × 5504'lük bir fotoğraf, belleğe tam
       boyutta açılmadan 2064 × 1376 olarak okunur.
    2. Fotoğrafın yön bilgisi (EXIF) uygulanır; telefonla dikey çekilmiş fotoğraf yan yatmaz.
    3. Oran korunarak en uzun kenar 1600 piksele indirilir; küçük görseller büyütülmez.
    4. WebP olarak kaydedilir. EXIF ve diğer üst veriler (konum, cihaz bilgisi) yeni dosyaya geçmez.
       Saydam görsellerin saydamlığı korunur; hareketli görselin ilk karesi alınır.
    """
    try:
        with Image.open(io.BytesIO(body)) as original:
            # Yalnızca JPEG'de etkilidir; diğer türlerde bir şey değiştirmez.
            original.draft(None, (MAX_DIMENSION, MAX_DIMENSION))
            image = ImageOps.exif_transpose(original)
            image = image.convert("RGBA" if _has_alpha(image) else "RGB")
            image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, format="WEBP", quality=WEBP_QUALITY, method=WEBP_METHOD)
    except (Image.DecompressionBombError, OSError, SyntaxError, ValueError) as error:
        raise NotAnImageError(f"Görsel dönüştürülemedi: {type(error).__name__}") from None
    width, height = image.size
    return ConvertedImage(body=output.getvalue(), width=width, height=height)


def _has_alpha(image: Image.Image) -> bool:
    """Görselde saydamlık var mı: saydamlık kanalı veya renk paletinde saydam renk."""
    return image.mode in _ALPHA_MODES or (image.mode == "P" and "transparency" in image.info)
