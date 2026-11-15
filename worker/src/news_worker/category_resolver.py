"""Bir haberin ortak kategorilerinin bulunması (ADR-0004, FG-VT-12, FG-VT-13).

Kategori iki düzeyde belirlenir:
- Besleme düzeyi: konuya özel beslemenin varsayılan kategorisi (TRT `ekonomi` beslemesi → Ekonomi).
- Haber düzeyi: haberin kaynakta belirtilen kendi kategori değeri, eşleme tablosundan ortak kategoriye çevrilir.
Hiçbir konu kategorisi atanamayan haber Diğer'e atanır.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from news_worker.text_normalizer import normalize_category

OTHER_CATEGORY_CODE = "OTHER"


class MappingLevel(StrEnum):
    """`article_categories.mapping_level` sütununun kabul ettiği değerler."""

    FEED = "FEED"
    ITEM = "ITEM"


@dataclass(frozen=True)
class AssignedCategory:
    category_code: str
    level: MappingLevel


@dataclass(frozen=True)
class FeedCategoryRule:
    """Beslemenin kategori ayarları (`feeds.default_category_id` ve `feeds.use_item_categories`)."""

    # Karışık içerikli beslemelerde boştur.
    default_category_code: str | None
    use_item_categories: bool


@dataclass(frozen=True)
class SourceCategoryMappings:
    """Bir kaynağın haber düzeyindeki eşlemeleri (`category_mappings`)."""

    # Kategori değerleri kaynağın dilinin kurallarıyla küçük harfe çevrilir.
    language: str
    # Normalleştirilmiş kaynak değeri → ortak kategori kodu.
    category_code_by_source_category: Mapping[str, str]


class CategoryResolver:
    def __init__(self, topic_category_codes: frozenset[str]) -> None:
        # Konu kategorileri (`categories.kind = 'TOPIC'`). Son Dakika bir zaman etiketidir, konu sayılmaz.
        self._topic_category_codes = topic_category_codes

    def resolve(
        self,
        source_categories: tuple[str, ...],
        feed_rule: FeedCategoryRule,
        mappings: SourceCategoryMappings,
    ) -> tuple[AssignedCategory, ...]:
        """Haberin kategorilerini döner; her kategori en çok bir kez yer alır."""
        # Sözlük: aynı kategori iki düzeyde de bulunursa ilk bulunan (besleme düzeyi) kalır.
        assigned: dict[str, MappingLevel] = {}
        if feed_rule.default_category_code is not None:
            assigned[feed_rule.default_category_code] = MappingLevel.FEED

        if feed_rule.use_item_categories:
            for source_category in source_categories:
                normalized = normalize_category(source_category, mappings.language)
                category_code = mappings.category_code_by_source_category.get(normalized)
                if category_code is not None:
                    assigned.setdefault(category_code, MappingLevel.ITEM)

        if not any(code in self._topic_category_codes for code in assigned):
            # Karar habere bakılarak verildiği için düzeyi ITEM'dır.
            assigned[OTHER_CATEGORY_CODE] = MappingLevel.ITEM

        return tuple(AssignedCategory(code, level) for code, level in assigned.items())
