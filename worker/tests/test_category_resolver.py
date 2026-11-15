from news_worker.category_resolver import (
    AssignedCategory,
    CategoryResolver,
    FeedCategoryRule,
    MappingLevel,
    SourceCategoryMappings,
)

# Son Dakika (BREAKING) bir zaman etiketidir; konu kategorileri arasında yer almaz.
TOPIC_CODES = frozenset(
    {"GENERAL", "WORLD", "ECONOMY", "SPORTS", "HEALTH", "SCIENCE_TECH", "CULTURE_ARTS", "LIFESTYLE", "OTHER"}
)

TURKISH_MAPPINGS = SourceCategoryMappings(
    language="tr",
    category_code_by_source_category={
        "türkiye": "GENERAL",
        "ekonomi": "ECONOMY",
        "eğitim": "LIFESTYLE",
        "yaşam": "LIFESTYLE",
    },
)

# Konuya özel besleme: kategori beslemeden gelir, haberin kendi değerine bakılmaz.
TOPIC_FEED = FeedCategoryRule(default_category_code="ECONOMY", use_item_categories=False)
# Karışık içerikli besleme: kategori yalnızca haberin kendi değerinden bulunur.
MIXED_FEED = FeedCategoryRule(default_category_code=None, use_item_categories=True)
# Son dakika beslemesi: zaman etiketi beslemeden, konu haberin kendi değerinden gelir.
BREAKING_FEED = FeedCategoryRule(default_category_code="BREAKING", use_item_categories=True)


def resolve(
    source_categories: tuple[str, ...],
    feed_rule: FeedCategoryRule,
    mappings: SourceCategoryMappings = TURKISH_MAPPINGS,
) -> tuple[AssignedCategory, ...]:
    return CategoryResolver(TOPIC_CODES).resolve(source_categories, feed_rule, mappings)


def test_feed_default_category_is_assigned_at_feed_level() -> None:
    """Konuya özel beslemenin haberi, beslemenin varsayılan kategorisini alır."""
    assert resolve((), TOPIC_FEED) == (AssignedCategory("ECONOMY", MappingLevel.FEED),)


def test_item_categories_are_ignored_when_feed_does_not_use_them() -> None:
    """Besleme haber düzeyi eşleme kullanmıyorsa haberin kendi değeri kategori eklemez."""
    assert resolve(("Türkiye",), TOPIC_FEED) == (AssignedCategory("ECONOMY", MappingLevel.FEED),)


def test_item_category_is_mapped_at_item_level() -> None:
    """Karışık beslemede haberin kendi değeri eşleme tablosundan ortak kategoriye çevrilir."""
    assert resolve(("Türkiye",), MIXED_FEED) == (AssignedCategory("GENERAL", MappingLevel.ITEM),)


def test_article_can_have_several_categories() -> None:
    """Bir haber birden fazla kategoriye sahip olabilir; sıra kaynaktaki sıradır."""
    assert resolve(("Ekonomi", "Türkiye"), MIXED_FEED) == (
        AssignedCategory("ECONOMY", MappingLevel.ITEM),
        AssignedCategory("GENERAL", MappingLevel.ITEM),
    )


def test_unmapped_candidates_are_ignored() -> None:
    """Eşleme tablosunda olmayan adaylar (adresteki `haber` klasörü gibi) elenir."""
    assert resolve(("haber", "ekonomi"), MIXED_FEED) == (AssignedCategory("ECONOMY", MappingLevel.ITEM),)


def test_same_category_from_two_values_is_assigned_once() -> None:
    """İki farklı kaynak değeri aynı ortak kategoriye gidiyorsa kategori bir kez atanır."""
    assert resolve(("Eğitim", "Yaşam"), MIXED_FEED) == (AssignedCategory("LIFESTYLE", MappingLevel.ITEM),)


def test_feed_level_wins_when_both_levels_give_same_category() -> None:
    """Aynı kategori iki düzeyde de bulunursa besleme düzeyi olarak kaydedilir."""
    feed_rule = FeedCategoryRule(default_category_code="ECONOMY", use_item_categories=True)

    assert resolve(("Ekonomi",), feed_rule) == (AssignedCategory("ECONOMY", MappingLevel.FEED),)


def test_source_category_is_matched_with_turkish_lowercase() -> None:
    """Kaynak değeri büyük harfle gelse de Türkçe kurallarıyla küçültülüp eşlenir."""
    assert resolve(("  EĞİTİM ",), MIXED_FEED) == (AssignedCategory("LIFESTYLE", MappingLevel.ITEM),)
    assert resolve(("TÜRKİYE",), MIXED_FEED) == (AssignedCategory("GENERAL", MappingLevel.ITEM),)


def test_article_without_any_topic_category_goes_to_other() -> None:
    """Hiçbir konu kategorisi atanamayan haber Diğer'e atanır (FG-VT-13)."""
    assert resolve(("infografik",), MIXED_FEED) == (AssignedCategory("OTHER", MappingLevel.ITEM),)
    assert resolve((), MIXED_FEED) == (AssignedCategory("OTHER", MappingLevel.ITEM),)


def test_breaking_is_not_a_topic_so_other_is_added() -> None:
    """Son Dakika konu sayılmaz: konusu bulunamayan son dakika haberi Diğer'i de alır."""
    assert resolve(("bilinmeyen",), BREAKING_FEED) == (
        AssignedCategory("BREAKING", MappingLevel.FEED),
        AssignedCategory("OTHER", MappingLevel.ITEM),
    )


def test_breaking_article_with_topic_does_not_get_other() -> None:
    """Konusu bulunan son dakika haberi hem Son Dakika'yı hem konusunu alır; Diğer eklenmez."""
    assert resolve(("Türkiye",), BREAKING_FEED) == (
        AssignedCategory("BREAKING", MappingLevel.FEED),
        AssignedCategory("GENERAL", MappingLevel.ITEM),
    )


def test_english_source_uses_default_and_matching_topics() -> None:
    """Global Voices: varsayılan Dünya; eşleşen konular eklenir, ülke ve bölge etiketleri eşlenmez."""
    mappings = SourceCategoryMappings(
        language="en",
        category_code_by_source_category={"health": "HEALTH", "arts & culture": "CULTURE_ARTS"},
    )
    feed_rule = FeedCategoryRule(default_category_code="WORLD", use_item_categories=True)

    assigned = resolve(("English", "Health", "Latin America", "Venezuela", "Arts & Culture"), feed_rule, mappings)

    assert assigned == (
        AssignedCategory("WORLD", MappingLevel.FEED),
        AssignedCategory("HEALTH", MappingLevel.ITEM),
        AssignedCategory("CULTURE_ARTS", MappingLevel.ITEM),
    )
