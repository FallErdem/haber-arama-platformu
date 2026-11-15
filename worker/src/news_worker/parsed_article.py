"""Beslemeden okunan bir haberin, kaynaktan bağımsız ortak yapısı (ADR-0013)."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ItemType(StrEnum):
    """`articles.item_type` sütununun kabul ettiği değerler."""

    ARTICLE = "ARTICLE"
    VIDEO = "VIDEO"
    GALLERY = "GALLERY"


@dataclass(frozen=True)
class ParsedArticle:
    """Okuyucunun ürettiği haber. Henüz veritabanına yazılmamıştır; kaydetme İ-12'dedir."""

    # Kaynağın habere verdiği kimlik (RSS'te guid, Atom'da id).
    external_id: str
    url: str
    # Tekrar kontrolünde kullanılır: aynı haberin farklı yazılmış adresleri aynı değere iner.
    normalized_url: str
    title: str
    # Düz metin; HTML içermez.
    summary: str | None
    # Temizlenmiş HTML; <img> etiketleri çıkarılmıştır.
    content: str | None
    author: str | None
    # Her zaman UTC.
    published_at: datetime
    item_type: ItemType
    # İlk adres haberin ana görselidir.
    image_urls: tuple[str, ...]
    # Kaynağın kendi kategori değerleri: kategori etiketleri, yoksa adresin klasör kısımları.
    # Ortak kategoriye çevirme CategoryResolver'ın işidir.
    source_categories: tuple[str, ...]
