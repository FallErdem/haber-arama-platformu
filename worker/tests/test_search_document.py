"""Haberin Elasticsearch belgesine çevrilmesinin testleri.

İlk bölüm belgenin içeriğini, ikinci bölüm üretilen belgenin gerçek Elasticsearch'te (kümedekiyle
aynı sürüm, işçinin yetkileriyle) kabul edildiğini ve arandığında bulunduğunu sınar.
"""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

import pytest
from elasticsearch import AsyncElasticsearch

from news_worker.search_document import (
    ArticleMetadata,
    ArticleTexts,
    build_document,
    document_id,
    metadata_fields,
    text_fields,
)
from news_worker.search_index import ALIAS, SearchIndex, index_name_for

ARTICLE_ID = UUID("019a0000-0000-7000-8000-000000000001")
PUBLISHED_AT = datetime(2026, 11, 13, 13, 40, tzinfo=UTC)

TURKISH = ArticleMetadata(
    id=ARTICLE_ID,
    source_code="TRT",
    language="tr",
    item_type="ARTICLE",
    published_at=PUBLISHED_AT,
    group_id=None,
    title="İstanbul'daki kitap fuarı açıldı",
    categories=("BREAKING", "CULTURE_ARTS"),
    hidden=False,
)

TURKISH_TEXTS = ArticleTexts(
    summary="Fuar bir hafta sürecek.",
    content=(
        '<p>Ziyaretçiler <a href="https://example.test/gizli-adres">kitapları</a> inceledi.</p><p>Işıklar yandı.</p>'
    ),
    author="Örnek Yazar",
)

ENGLISH = replace(
    TURKISH, source_code="GLOBALVOICES", language="en", title="Volunteers are running a library", categories=("WORLD",)
)

ENGLISH_TEXTS = ArticleTexts(summary="A short summary.", content="<p>The readers borrowed books.</p>", author=None)


def test_turkish_article_fills_turkish_fields() -> None:
    """Türkçe haberin metinleri `_tr` alanlarına yazılır; `_en` alanları belgede yer almaz."""
    document = build_document(TURKISH, TURKISH_TEXTS)

    assert document == {
        "source_code": "TRT",
        "language": "tr",
        "item_type": "ARTICLE",
        "categories": ["BREAKING", "CULTURE_ARTS"],
        "published_at": PUBLISHED_AT,
        "group_id": None,
        "hidden": False,
        "title_tr": "İstanbul'daki kitap fuarı açıldı",
        "summary_tr": "Fuar bir hafta sürecek.",
        "content_tr": TURKISH_TEXTS.content,
        "author": "Örnek Yazar",
    }


def test_english_article_fills_english_fields() -> None:
    """İngilizce haberin metinleri `_en` alanlarına yazılır."""
    document = build_document(ENGLISH, ENGLISH_TEXTS)

    assert document["title_en"] == "Volunteers are running a library"
    assert document["summary_en"] == "A short summary."
    assert document["content_en"] == "<p>The readers borrowed books.</p>"
    assert not any(field.endswith("_tr") for field in document)


def test_metadata_fields_carry_no_texts() -> None:
    """Meta veri alanları metin taşımaz: meta veri güncellenirken belgedeki metinlere dokunulmaz (ADR-0019)."""
    fields = metadata_fields(TURKISH)

    assert set(fields) == {
        "source_code",
        "language",
        "item_type",
        "categories",
        "published_at",
        "group_id",
        "hidden",
        "title_tr",
    }


def test_hidden_flag_and_group_are_part_of_metadata() -> None:
    """Gizleme bilgisi ve grup kimliği meta veridir; grup kimliği yoksa boş yazılır (gruptan çıkma da yansır)."""
    group_id = UUID("019a0000-0000-7000-8000-0000000000aa")

    assert metadata_fields(replace(TURKISH, hidden=True))["hidden"] is True
    assert metadata_fields(replace(TURKISH, group_id=group_id))["group_id"] == str(group_id)
    assert metadata_fields(TURKISH)["group_id"] is None


def test_content_is_kept_as_html() -> None:
    """Tam metin HTML olarak yazılır: tek kopyası burada ve detay sayfası paragrafları gösterir (ADR-0019).

    Etiketlerin ve bağlantı adreslerinin aranmadığını aşağıdaki gerçek Elasticsearch testi gösterir.
    """
    assert text_fields("tr", TURKISH_TEXTS)["content_tr"].startswith("<p>Ziyaretçiler <a href=")


def test_missing_texts_are_left_out() -> None:
    """Özeti, içeriği ve yazarı olmayan haberde (CNN Türk içerik ve yazar vermez) bu alanlar belgeye konmaz."""
    assert text_fields("tr", ArticleTexts(summary=None, content=None, author=None)) == {}


def test_content_without_any_text_is_left_out() -> None:
    """Yalnızca etiketten oluşan içerikten yazı çıkmaz; boş alan yazılmaz."""
    assert "content_tr" not in text_fields("tr", replace(TURKISH_TEXTS, content="<p> </p>"))


def test_texts_survive_the_trip_through_the_outbox_note() -> None:
    """Metinler outbox notuna JSON olarak yazılıp aynen geri okunur."""
    assert ArticleTexts.from_payload(TURKISH_TEXTS.to_payload()) == TURKISH_TEXTS


def test_document_id_is_the_article_id() -> None:
    """Belge kimliği haber kimliğidir; aynı haber yeniden gönderilince ikinci belge oluşmaz."""
    assert document_id(ARTICLE_ID) == "019a0000-0000-7000-8000-000000000001"


# --- Gerçek Elasticsearch ---------------------------------------------------------------------


async def store(
    search_client: AsyncElasticsearch, metadata: ArticleMetadata = TURKISH, texts: ArticleTexts = TURKISH_TEXTS
) -> None:
    await search_client.index(
        index=index_name_for(metadata.published_at),
        id=document_id(metadata.id),
        document=build_document(metadata, texts),
        refresh=True,
    )


async def search_ids(search_client: AsyncElasticsearch, field: str, text: str) -> list[str]:
    response = await search_client.search(index=ALIAS, query={"match": {field: text}})
    return [hit["_id"] for hit in response["hits"]["hits"]]


async def test_built_document_is_accepted_by_the_index(search_client: AsyncElasticsearch) -> None:
    """Üretilen belgenin bütün alanları şablonda tanımlıdır: `strict` şablon belgeyi reddetmez."""
    await SearchIndex(search_client).ensure_ready()

    await store(search_client, replace(TURKISH, group_id=UUID("019a0000-0000-7000-8000-0000000000aa")))
    await store(search_client, replace(ENGLISH, id=UUID("019a0000-0000-7000-8000-000000000002")), ENGLISH_TEXTS)

    assert (await search_client.count(index=ALIAS))["count"] == 2
    stored = await search_client.get(index="articles-g1-2026.11.01", id=str(ARTICLE_ID))
    assert stored["_source"]["published_at"] == "2026-11-13T13:40:00+00:00"
    assert stored["_source"]["categories"] == ["BREAKING", "CULTURE_ARTS"]
    assert stored["_source"]["hidden"] is False


async def test_turkish_article_is_found_by_differently_inflected_words(search_client: AsyncElasticsearch) -> None:
    """Türkçe haber, metindeki kelimelerin başka ekli ve başka büyük/küçük harfli halleriyle bulunur."""
    await SearchIndex(search_client).ensure_ready()
    await store(search_client)

    # Başlıkta "İstanbul'daki", içerikte "kitapları" ve "Işıklar" geçiyor.
    assert await search_ids(search_client, "title_tr", "istanbul") == [str(ARTICLE_ID)]
    assert await search_ids(search_client, "content_tr", "kitap") == [str(ARTICLE_ID)]
    assert await search_ids(search_client, "content_tr", "IŞIK") == [str(ARTICLE_ID)]


@pytest.mark.parametrize(
    ("field", "text"),
    [
        ("title_tr", "ISTANBUL"),
        ("title_tr", "Istanbul"),
        ("title_tr", "acildi"),
        ("content_tr", "ziyaretciler"),
        ("content_tr", "isiklar"),
    ],
)
async def test_turkish_article_is_found_without_turkish_letters(
    search_client: AsyncElasticsearch, field: str, text: str
) -> None:
    """Türkçe karaktersiz veya noktasız büyük I ile yazılan sorgu asıl alanda değil, katlanmış alt alanda bulunur."""
    await SearchIndex(search_client).ensure_ready()
    await store(search_client)

    assert await search_ids(search_client, field, text) == []
    assert await search_ids(search_client, f"{field}.folded", text) == [str(ARTICLE_ID)]


async def test_plural_only_article_is_found_by_singular_word(search_client: AsyncElasticsearch) -> None:
    """Yalnızca "seçimler" geçen haber "seçim" aramasıyla asıl alanda bulunamaz; katlanmış alt alanda bulunur."""
    await SearchIndex(search_client).ensure_ready()
    await store(search_client, replace(TURKISH, title="Seçimler ertelendi"))

    assert await search_ids(search_client, "title_tr", "seçim") == []
    assert await search_ids(search_client, "title_tr.folded", "seçim") == [str(ARTICLE_ID)]


async def test_link_addresses_in_content_are_not_searchable(search_client: AsyncElasticsearch) -> None:
    """İçerikteki bağlantının adresi indekse girmez; adresteki kelimeyle haber bulunmaz."""
    await SearchIndex(search_client).ensure_ready()
    await store(search_client)

    assert await search_ids(search_client, "content_tr", "gizli") == []


async def test_html_tags_in_content_are_not_searchable(search_client: AsyncElasticsearch) -> None:
    """Tam metin HTML olarak saklanır, ama etiket ve öznitelik adları aranabilir kelime olmaz (html_strip)."""
    await SearchIndex(search_client).ensure_ready()
    await store(search_client)

    for word in ("href", "example", "https"):
        assert await search_ids(search_client, "content_tr", word) == []
        assert await search_ids(search_client, "content_tr.folded", word) == []
    # Metnin kendisi aranır.
    assert await search_ids(search_client, "content_tr", "ziyaretçi") == [str(ARTICLE_ID)]


async def test_html_entities_in_content_are_searched_as_letters(search_client: AsyncElasticsearch) -> None:
    """HTML kodlanmış karakterler çözülerek aranır: "&Ccedil;ocuklar" Çocuklar, "&#351;ehir" şehir olarak okunur."""
    await SearchIndex(search_client).ensure_ready()
    texts = replace(TURKISH_TEXTS, content="<p>&Ccedil;ocuklar &#351;ehir k&#252;t&#252;phanesinde</p>")
    await store(search_client, TURKISH, texts)

    assert await search_ids(search_client, "content_tr", "çocuk") == [str(ARTICLE_ID)]
    assert await search_ids(search_client, "content_tr", "şehir") == [str(ARTICLE_ID)]


async def test_stored_document_keeps_html_content_and_author(search_client: AsyncElasticsearch) -> None:
    """Belgede tam metin HTML olarak ve yazar olduğu gibi durur; detay sayfası onları buradan okur."""
    await SearchIndex(search_client).ensure_ready()
    await store(search_client)

    stored = await search_client.get(index="articles-g1-2026.11.01", id=str(ARTICLE_ID))

    assert stored["_source"]["content_tr"] == TURKISH_TEXTS.content
    assert stored["_source"]["author"] == "Örnek Yazar"


async def test_author_is_not_searchable(search_client: AsyncElasticsearch) -> None:
    """Yazar yalnızca gösterilir; yazar adıyla arama yapılmaz."""
    await SearchIndex(search_client).ensure_ready()
    await store(search_client)

    response = await search_client.search(index=ALIAS, query={"query_string": {"query": "Örnek Yazar"}})

    assert response["hits"]["hits"] == []


async def test_english_article_is_found_by_word_stem(search_client: AsyncElasticsearch) -> None:
    """İngilizce haber İngilizce analizörle işlenir: "running" kelimesi "run" aramasıyla bulunur."""
    await SearchIndex(search_client).ensure_ready()
    await store(search_client, ENGLISH, ENGLISH_TEXTS)

    assert await search_ids(search_client, "title_en", "run") == [str(ARTICLE_ID)]
    assert await search_ids(search_client, "content_en", "book") == [str(ARTICLE_ID)]


async def test_sending_the_same_article_again_overwrites_the_document(search_client: AsyncElasticsearch) -> None:
    """Aynı haber iki kez gönderilirse tek belge kalır ve son gönderilen içerik geçerlidir."""
    await SearchIndex(search_client).ensure_ready()
    await store(search_client)

    await store(search_client, replace(TURKISH, categories=("CULTURE_ARTS",)))

    assert (await search_client.count(index=ALIAS))["count"] == 1
    stored = await search_client.get(index="articles-g1-2026.11.01", id=str(ARTICLE_ID))
    assert stored["_source"]["categories"] == ["CULTURE_ARTS"]
