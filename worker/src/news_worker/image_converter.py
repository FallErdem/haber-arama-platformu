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

    Bellekte görüntünün tek bir kopyası tutulur: yön düzeltme yerinde yapılır, renk kipi yalnızca
    farklıysa çevrilir. İşçinin bellek sınırı içinde büyük fotoğraflar da güvenle çevrilir.
    """
    try:
        with Image.open(io.BytesIO(body)) as image:
            # Yalnızca JPEG'de etkilidir; diğer türlerde bir şey değiştirmez.
            image.draft(None, _target_size(image.size))
            image.load()
            ImageOps.exif_transpose(image, in_place=True)
            target_mode = "RGBA" if _has_alpha(image) else "RGB"
            # convert() aynı kipte de yeni bir kopya üretir; yalnızca gerektiğinde çağrılır.
            prepared: Image.Image = image if image.mode == target_mode else image.convert(target_mode)
            prepared.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            prepared.save(output, format="WEBP", quality=WEBP_QUALITY, method=WEBP_METHOD)
            width, height = prepared.size
    except (Image.DecompressionBombError, OSError, SyntaxError, ValueError) as error:
        raise NotAnImageError(f"Görsel dönüştürülemedi: {type(error).__name__}") from None
    return ConvertedImage(body=output.getvalue(), width=width, height=height)


def _target_size(size: tuple[int, int]) -> tuple[int, int]:
    """Görselin, en uzun kenarı 1600 piksel olacak şekilde oranı korunmuş boyutu (8256 × 5504 → 1600 × 1067).

    Taslak kipine kare bir hedef (1600 × 1600) verilirse Pillow iki kenarı da bu karenin altına düşmeyecek
    kadar küçültür; yatay fotoğrafta kısa kenar belirleyici olur ve görüntü gereğinden büyük çözülür.
    """
    width, height = size
    ratio = min(1.0, MAX_DIMENSION / max(width, height))
    return max(1, round(width * ratio)), max(1, round(height * ratio))


def _has_alpha(image: Image.Image) -> bool:
    """Görselde saydamlık var mı: saydamlık kanalı veya renk paletinde saydam renk."""
    return image.mode in _ALPHA_MODES or (image.mode == "P" and "transparency" in image.info)
