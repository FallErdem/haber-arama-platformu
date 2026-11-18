"""Bir haberin Elasticsearch belgesine çevrilmesi (`05-veri-modeli.md` 5.2).

Belge; filtre alanlarını (kaynak, dil, tür, kategoriler, tarih), haberin diline göre doldurulan metin
alanlarını ve yazarı taşır. Özet, tam metin ve yazarın tek kopyası Elasticsearch'tedir (ADR-0019).
Görseller ve kaynak adı belgede yoktur; gösterilirken PostgreSQL'den okunur.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from news_worker.html_cleaner import to_plain_text


@dataclass(frozen=True)
class IndexableArticle:
    """Haberin arama indeksine yazılacak hali; PostgreSQL'den kaynak kodu ve kategori kodlarıyla okunur."""

    id: UUID
    source_code: str
    # "tr" veya "en"; metinlerin hangi alanlara yazılacağını belirler.
    language: str
    item_type: str
    published_at: datetime
    group_id: UUID | None
    title: str
    summary: str | None
    # Temizlenmiş HTML (işçinin nh3 ile temizlediği hali).
    content: str | None
    author: str | None
    categories: tuple[str, ...]


def document_id(article: IndexableArticle) -> str:
    """Belge kimliği haberin kimliğidir: aynı haber yeniden gönderilirse ikinci bir belge oluşmaz,
    var olan belgenin üzerine yazılır."""
    return str(article.id)


def build_document(article: IndexableArticle) -> dict[str, Any]:
    """Haberi Elasticsearch belgesine çevirir.

    Metinler haberin diline ait alanlara yazılır (`title_tr` veya `title_en`); her alan kendi dilinin
    analizörüyle işlenir. Değeri olmayan alanlar belgeye hiç konmaz.
    """
    document: dict[str, Any] = {
        "source_code": article.source_code,
        "language": article.language,
        "item_type": article.item_type,
        "categories": list(article.categories),
        "published_at": article.published_at,
        f"title_{article.language}": article.title,
    }
    if article.group_id is not None:
        document["group_id"] = str(article.group_id)
    if article.summary:
        document[f"summary_{article.language}"] = article.summary
    # İçerik HTML olarak yazılır: detay sayfası paragrafları gösterir. Etiketleri arama analizörü atar
    # (html_strip); etiket adları ve bağlantı adresleri aranabilir kelime olmaz. Yazısı olmayan içerik
    # ("<p> </p>") yazılmaz.
    if article.content and to_plain_text(article.content):
        document[f"content_{article.language}"] = article.content
    if article.author:
        document["author"] = article.author
    return document
