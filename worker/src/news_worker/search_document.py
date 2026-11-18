"""Bir haberin Elasticsearch belgesine çevrilmesi (`05-veri-modeli.md` 5.2; ADR-0019).

Belgenin iki kaynağı vardır:

- **Meta veri** (`ArticleMetadata`): PostgreSQL'den okunur; kaynak, dil, tür, kategoriler, tarih,
  başlık, gizleme bilgisi. Değiştiğinde belgenin yalnızca bu alanları güncellenir.
- **Metinler** (`ArticleTexts`): özet, tam metin (HTML) ve yazar. Tek kayıtları Elasticsearch'tir;
  haber kaydedilirken outbox notuyla taşınır ve belge ilk yazılırken bir kez gönderilir.

Görseller ve kaynak adı belgede yoktur; gösterilirken PostgreSQL'den okunur.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from news_worker.html_cleaner import to_plain_text


@dataclass(frozen=True)
class ArticleMetadata:
    """Haberin PostgreSQL'deki meta verisi; kaynak kodu ve kategori kodlarıyla birlikte okunur."""

    id: UUID
    source_code: str
    # "tr" veya "en"; metinlerin hangi alanlara yazılacağını belirler.
    language: str
    item_type: str
    published_at: datetime
    group_id: UUID | None
    title: str
    categories: tuple[str, ...]
    # Gizlenen haber indekste kalır ama aramada görünmez; metni yalnızca burada olduğu için silinmez.
    hidden: bool


@dataclass(frozen=True)
class ArticleTexts:
    """Haberin metinleri. Outbox notunda JSON olarak taşınır (`outbox_events.payload`)."""

    summary: str | None
    # İşçinin nh3 ile temizlediği HTML.
    content: str | None
    author: str | None

    def to_payload(self) -> dict[str, str | None]:
        return {"summary": self.summary, "content": self.content, "author": self.author}

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> ArticleTexts:
        return cls(summary=payload.get("summary"), content=payload.get("content"), author=payload.get("author"))


def document_id(article_id: UUID) -> str:
    """Belge kimliği haberin kimliğidir: aynı haber yeniden gönderilirse ikinci bir belge oluşmaz,
    var olan belgenin üzerine yazılır."""
    return str(article_id)


def metadata_fields(article: ArticleMetadata) -> dict[str, Any]:
    """Belgenin meta veri alanları. Meta veri değiştiğinde belgede yalnızca bunlar güncellenir.

    Grup kimliği yoksa alan boş (null) yazılır; böylece bir haberin gruptan çıkarılması da belgeye yansır.
    """
    return {
        "source_code": article.source_code,
        "language": article.language,
        "item_type": article.item_type,
        "categories": list(article.categories),
        "published_at": article.published_at,
        "group_id": str(article.group_id) if article.group_id is not None else None,
        "hidden": article.hidden,
        f"title_{article.language}": article.title,
    }


def text_fields(language: str, texts: ArticleTexts) -> dict[str, Any]:
    """Belgenin metin alanları; haberin diline ait alanlara yazılır. Değeri olmayan alan yazılmaz.

    Tam metin HTML olarak yazılır: detay sayfası paragrafları gösterir. Etiketleri arama analizörü atar
    (html_strip). Yazısı olmayan içerik ("<p> </p>") yazılmaz.
    """
    fields: dict[str, Any] = {}
    if texts.summary:
        fields[f"summary_{language}"] = texts.summary
    if texts.content and to_plain_text(texts.content):
        fields[f"content_{language}"] = texts.content
    if texts.author:
        fields["author"] = texts.author
    return fields


def build_document(article: ArticleMetadata, texts: ArticleTexts) -> dict[str, Any]:
    """Haberin bütün belgesi: meta veri ve metinler. Belge ilk yazılırken kullanılır."""
    return {**metadata_fields(article), **text_fields(article.language, texts)}
