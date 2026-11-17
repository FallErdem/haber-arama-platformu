"""Görsellerin ortak biçime (WebP, en fazla 1600 piksel) çevrilmesinin testleri."""

import io

import pytest
from conftest import make_image
from PIL import Image

from news_worker.image_converter import MAX_DIMENSION, convert_to_webp
from news_worker.image_downloader import NotAnImageError

# EXIF'teki yön etiketi: 6 = "90 derece döndürerek göster" (telefonla dikey çekilmiş fotoğraf).
ORIENTATION_TAG = 0x0112


def open_result(body: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(body))
    image.load()
    return image


@pytest.mark.parametrize("image_format", ["JPEG", "PNG", "WEBP", "GIF"])
def test_every_supported_type_becomes_webp(image_format: str) -> None:
    """Kabul edilen her tür WebP'ye çevrilir."""
    result = convert_to_webp(make_image(image_format, size=(300, 200)))

    assert result.content_type == "image/webp"
    assert open_result(result.body).format == "WEBP"
    assert (result.width, result.height) == (300, 200)


def test_large_photo_is_scaled_down_keeping_its_proportions() -> None:
    """En uzun kenar 1600 piksele indirilir; oran korunur (8256 × 5504 → 1600 × 1067)."""
    result = convert_to_webp(make_image("JPEG", size=(8256, 5504)))

    assert (result.width, result.height) == (1600, 1067)
    assert open_result(result.body).size == (1600, 1067)


def test_tall_image_is_limited_by_its_height() -> None:
    """Dikey görselde sınır yüksekliğe uygulanır."""
    result = convert_to_webp(make_image("PNG", size=(1000, 4000)))

    assert (result.width, result.height) == (400, MAX_DIMENSION)


def test_small_image_is_not_enlarged() -> None:
    """Sınırdan küçük görsel büyütülmez."""
    result = convert_to_webp(make_image("JPEG", size=(640, 480)))

    assert (result.width, result.height) == (640, 480)


def test_transparency_is_kept() -> None:
    """Saydam PNG'nin saydamlığı WebP'de korunur."""
    buffer = io.BytesIO()
    Image.new("RGBA", (50, 50), color=(255, 0, 0, 0)).save(buffer, format="PNG")

    result = open_result(convert_to_webp(buffer.getvalue()).body)

    assert result.mode == "RGBA"
    pixel = result.getpixel((10, 10))
    assert isinstance(pixel, tuple)
    assert pixel[3] == 0


def test_opaque_image_has_no_transparency_channel() -> None:
    """Saydamlığı olmayan görsele gereksiz saydamlık kanalı eklenmez."""
    assert open_result(convert_to_webp(make_image("PNG")).body).mode == "RGB"


def test_photo_orientation_is_applied_and_metadata_is_removed() -> None:
    """Dikey çekilmiş fotoğraf yan yatmaz; EXIF (konum, cihaz bilgisi) yeni dosyaya geçmez."""
    exif = Image.Exif()
    exif[ORIENTATION_TAG] = 6
    buffer = io.BytesIO()
    # Piksel olarak yatay (300 × 200) kaydedilmiş, "90 derece döndür" etiketi taşıyan fotoğraf.
    Image.new("RGB", (300, 200), color=(0, 0, 255)).save(buffer, format="JPEG", exif=exif.tobytes())

    result = convert_to_webp(buffer.getvalue())

    assert (result.width, result.height) == (200, 300)
    assert not open_result(result.body).getexif()


def test_animated_gif_keeps_its_first_frame() -> None:
    """Hareketli görselin ilk karesi alınır; sonuç hareketsizdir."""
    frames = [Image.new("RGB", (40, 30), color=color) for color in ((255, 0, 0), (0, 255, 0))]
    buffer = io.BytesIO()
    frames[0].save(buffer, format="GIF", save_all=True, append_images=frames[1:], duration=100)

    result = open_result(convert_to_webp(buffer.getvalue()).body)

    assert getattr(result, "is_animated", False) is False
    pixel = result.convert("RGB").getpixel((5, 5))
    assert isinstance(pixel, tuple)
    assert pixel[0] > 200 and pixel[1] < 50


def test_large_png_becomes_much_smaller() -> None:
    """Fotoğraf gibi ayrıntılı bir PNG, WebP'de belirgin küçülür (kümede ortalama PNG 1 MB).

    Tek renkli bir görsel PNG'de de çok küçük olduğundan, fotoğrafa benzemesi için gürültü eklenir.
    """
    noise = Image.effect_noise((1920, 1280), 60)
    buffer = io.BytesIO()
    Image.merge("RGB", (noise, noise.rotate(90, expand=False), noise.transpose(Image.Transpose.FLIP_LEFT_RIGHT))).save(
        buffer, format="PNG"
    )
    original = buffer.getvalue()

    result = convert_to_webp(original)

    assert len(result.body) < len(original) / 5


def test_broken_file_cannot_be_converted() -> None:
    """Açılamayan dosya için anlaşılır bir hata fırlatılır."""
    with pytest.raises(NotAnImageError, match="dönüştürülemedi"):
        convert_to_webp(make_image("JPEG")[:100])
