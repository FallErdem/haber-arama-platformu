"""Arama indeksi kurulumunun testleri.

Elasticsearch gerçektir (kümedekiyle aynı sürüm, geçici konteyner) ve testler işçinin kendi
kullanıcısıyla, onun yetkileriyle çalışır.
"""

import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from elasticsearch import AsyncElasticsearch, BadRequestError

from news_worker.search_index import (
    ALIAS,
    COLD_AFTER_DAYS,
    POLICY_NAME,
    WARM_AFTER_DAYS,
    SearchIndex,
    index_name_for,
    search_structure,
    template_name_for,
)

NOVEMBER_INDEX = "articles-g1-2026.11.01"

# API'nin testlerinde kullanılan indeks yapısı; depo kökünden bakılır.
API_TEST_STRUCTURE = (
    Path(__file__).resolve().parents[2] / "backend/src/test/resources/search/articles-index-structure.json"
)


def test_api_tests_use_the_same_index_structure() -> None:
    """API'nin testlerindeki indeks yapısı (alanlar, analizörler) işçinin kurduğuyla birebir aynıdır (R-36).

    Bu test kırılırsa şablon değişmiştir; dosya şu komutla yeniden üretilir ve API testleri yeni yapıyla çalışır:
    `uv run python -c "import json; from news_worker.search_index import search_structure;
    print(json.dumps(search_structure(), indent=2, ensure_ascii=False))"`
    """
    assert json.loads(API_TEST_STRUCTURE.read_text(encoding="utf-8")) == search_structure()


def test_index_name_is_first_day_of_publication_month() -> None:
    """Haber, yayın tarihinin ayına ait indekse yazılır; indeks adı ayın ilk gününü taşır."""
    assert index_name_for(datetime(2026, 11, 13, 13, 40, tzinfo=UTC)) == NOVEMBER_INDEX
    assert index_name_for(datetime(2023, 6, 6, 16, 2, tzinfo=UTC)) == "articles-g1-2023.06.01"


def test_index_month_is_decided_in_utc() -> None:
    """Ay, UTC'ye göre belirlenir: Türkiye saatiyle 1 Aralık 01:00, UTC'de hâlâ 30 Kasım'dır."""
    turkey_time = timezone(timedelta(hours=3))

    assert index_name_for(datetime(2026, 12, 1, 1, 0, tzinfo=turkey_time)) == NOVEMBER_INDEX


def test_index_name_carries_the_generation() -> None:
    """Tam yeniden indeksleme yeni bir nesle yazar; nesil indeks adında yer alır."""
    assert index_name_for(datetime(2026, 11, 13, tzinfo=UTC), generation=2) == "articles-g2-2026.11.01"


async def test_setup_creates_lifecycle_policy_with_documented_thresholds(search_client: AsyncElasticsearch) -> None:
    """Yaşam döngüsü politikası oluşur: 60 günde ılık (birleştirme), 395 günde soğuk (düşük öncelik)."""
    await SearchIndex(search_client).ensure_ready()

    response = await search_client.ilm.get_lifecycle(name=POLICY_NAME)
    phases = response[POLICY_NAME]["policy"]["phases"]
    assert phases["warm"] == {"min_age": f"{WARM_AFTER_DAYS}d", "actions": {"forcemerge": {"max_num_segments": 1}}}
    assert phases["cold"] == {"min_age": f"{COLD_AFTER_DAYS}d", "actions": {"set_priority": {"priority": 0}}}
    assert (WARM_AFTER_DAYS, COLD_AFTER_DAYS) == (60, 395)


async def test_setup_can_run_again_without_breaking_anything(search_client: AsyncElasticsearch) -> None:
    """Kurulum her açılışta çalışır; ikinci kez çalıştığında hata vermez ve var olan belgeler durur."""
    index = SearchIndex(search_client)
    await index.ensure_ready()
    await search_client.index(index=NOVEMBER_INDEX, id="haber-1", document={"language": "tr"}, refresh=True)

    await index.ensure_ready()

    assert (await search_client.count(index=ALIAS))["count"] == 1
    templates = await search_client.indices.get_index_template(name="articles*")
    assert len(templates["index_templates"]) == 1


async def test_monthly_index_is_created_from_template_on_first_write(search_client: AsyncElasticsearch) -> None:
    """Aylık indeks elle oluşturulmaz: ilk belge yazıldığında şablondaki alanlar ve analizörlerle açılır."""
    await SearchIndex(search_client).ensure_ready()

    await search_client.index(index=NOVEMBER_INDEX, id="haber-1", document={"language": "tr"})

    mapping = await search_client.indices.get_mapping(index=NOVEMBER_INDEX)
    properties = mapping[NOVEMBER_INDEX]["mappings"]["properties"]
    turkish_text = {
        "type": "text",
        "analyzer": "turkish",
        "fields": {"folded": {"type": "text", "analyzer": "turkish_folded"}},
    }
    assert properties["title_tr"] == turkish_text
    assert properties["summary_tr"] == turkish_text
    assert properties["content_tr"] == turkish_text
    assert properties["title_en"] == {"type": "text", "analyzer": "english"}
    assert properties["categories"] == {"type": "keyword"}
    assert properties["published_at"] == {"type": "date"}
    settings = (await search_client.indices.get_settings(index=NOVEMBER_INDEX))[NOVEMBER_INDEX]["settings"]["index"]
    assert settings["lifecycle"]["name"] == POLICY_NAME
    assert settings["number_of_replicas"] == "0"


async def test_every_monthly_index_is_searchable_through_the_alias(search_client: AsyncElasticsearch) -> None:
    """Farklı aylara yazılan belgeler tek bir takma ad üzerinden birlikte aranır."""
    await SearchIndex(search_client).ensure_ready()
    await search_client.index(index=NOVEMBER_INDEX, id="yeni", document={"language": "tr"}, refresh=True)
    await search_client.index(index="articles-g1-2023.06.01", id="eski", document={"language": "tr"}, refresh=True)

    response = await search_client.search(index=ALIAS, query={"match_all": {}})

    assert {hit["_id"] for hit in response["hits"]["hits"]} == {"yeni", "eski"}


async def test_index_age_is_taken_from_its_name(search_client: AsyncElasticsearch) -> None:
    """İndeksin yaşı oluşturulma anından değil adındaki tarihten sayılır; eski tarihli indeks baştan yaşlıdır."""
    await SearchIndex(search_client).ensure_ready()

    await search_client.index(index="articles-g1-2023.06.01", id="eski", document={"language": "tr"})

    explained = await search_client.ilm.explain_lifecycle(index="articles-g1-2023.06.01")
    lifecycle = explained["indices"]["articles-g1-2023.06.01"]
    assert lifecycle["managed"] is True
    assert lifecycle["policy"] == POLICY_NAME
    origination = datetime.fromtimestamp(lifecycle["lifecycle_date_millis"] / 1000, tz=UTC)
    assert origination == datetime(2023, 6, 1, tzinfo=UTC)


async def test_unknown_field_is_rejected(search_client: AsyncElasticsearch) -> None:
    """Şablonda tanımlı olmayan bir alan gönderilirse belge reddedilir; yazım hatası yeni alan oluşturamaz."""
    await SearchIndex(search_client).ensure_ready()

    with pytest.raises(BadRequestError, match="strict_dynamic_mapping_exception"):
        await search_client.index(index=NOVEMBER_INDEX, id="haber-1", document={"tilte_tr": "yazım hatası"})


async def test_turkish_analyzer_handles_suffixes_and_dotted_i(search_client: AsyncElasticsearch) -> None:
    """Türkçe analizör ekleri atar ve İ/i, I/ı kurallarını uygular (FG-AR-11)."""
    await SearchIndex(search_client).ensure_ready()
    await search_client.index(index=NOVEMBER_INDEX, id="haber-1", document={"language": "tr"})

    response = await search_client.indices.analyze(
        index=NOVEMBER_INDEX, field="title_tr", text="İstanbul'daki KİTAPLARI ışıklar"
    )

    assert [token["token"] for token in response["tokens"]] == ["istanbul", "kitap", "ışık"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Türkçe karakterli, karaktersiz, noktalı ve noktasız büyük harfli yazımlar aynı sonuca iner.
        ("İstanbul ISTANBUL istanbul Istanbul", ["istan", "istan", "istan", "istan"]),
        ("Cumhurbaşkanı cumhurbaskani", ["cumhu", "cumhu"]),
        ("Türkiye'nin turkiye TÜRKİYE", ["turki", "turki", "turki"]),
        # Yerleşik kök bulucunun farklı köke indirdiği tekil ve çoğul aynı sonuca iner.
        ("seçim seçimler deprem depremler", ["secim", "secim", "depre", "depre"]),
        # Şapkalı harfler şapkasız karşılıklarıyla aynıdır; kısa kelimeler kesilmez.
        ("hâlâ hala zekâ zeka", ["hala", "hala", "zeka", "zeka"]),
        # Etkisiz kelimeler atılmaz: bu alan asıl alanın yanında yalnızca ek eşleşme sağlar.
        ("bir ve Iğdır", ["bir", "ve", "igdir"]),
    ],
    ids=["dotted-and-dotless-i", "ascii-typing", "apostrophe", "singular-plural", "circumflex", "short-words"],
)
async def test_folded_subfield_reduces_spelling_variants_to_one_form(
    search_client: AsyncElasticsearch, text: str, expected: list[str]
) -> None:
    """Katlanmış alt alan, aynı kelimenin farklı yazımlarını tek biçime indirir."""
    await SearchIndex(search_client).ensure_ready()
    await search_client.index(index=NOVEMBER_INDEX, id="haber-1", document={"language": "tr"})

    response = await search_client.indices.analyze(index=NOVEMBER_INDEX, field="title_tr.folded", text=text)

    assert [token["token"] for token in response["tokens"]] == expected


async def test_english_fields_have_no_folded_subfield(search_client: AsyncElasticsearch) -> None:
    """Katlanmış alt alan yalnızca Türkçe alanlardadır; İngilizce alanlar olduğu gibi kalır."""
    await SearchIndex(search_client).ensure_ready()
    await search_client.index(index=NOVEMBER_INDEX, id="haber-1", document={"language": "en"})

    mapping = await search_client.indices.get_mapping(index=NOVEMBER_INDEX)

    assert mapping[NOVEMBER_INDEX]["mappings"]["properties"]["title_en"] == {"type": "text", "analyzer": "english"}


# --- Nesiller ------------------------------------------------------------------------------------


async def put_legacy_template(client: AsyncElasticsearch) -> None:
    """İlk sürümün kurduğu tek şablon: adı `articles`, kapsamı bütün nesiller, takma adı taşır."""
    await client.indices.put_index_template(
        name="articles", index_patterns=["articles-*"], template={"aliases": {ALIAS: {}}}
    )


async def test_first_generation_is_active_on_an_empty_elasticsearch(search_client: AsyncElasticsearch) -> None:
    """Hiç şablon yokken etkin nesil 1'dir ve kurulum 1. neslin şablonunu oluşturur."""
    index = SearchIndex(search_client)

    assert await index.active_generation() == 1
    await index.ensure_ready()

    templates = await search_client.indices.get_index_template(name=template_name_for(1))
    template = templates["index_templates"][0]["index_template"]
    assert template["index_patterns"] == ["articles-g1-*"]
    assert ALIAS in template["template"]["aliases"]


async def test_active_generation_is_the_one_whose_template_carries_the_alias(
    search_client: AsyncElasticsearch,
) -> None:
    """Etkin nesil, takma adı taşıyan şablonun neslidir; takma adsız (doldurulmakta olan) nesil sayılmaz."""
    index = SearchIndex(search_client)
    await index.put_template(2, searchable=True)
    await index.put_template(3, searchable=False)

    assert await index.active_generation() == 2


async def test_legacy_template_counts_as_first_generation(search_client: AsyncElasticsearch) -> None:
    """İlk sürümün tek şablonuyla (`articles`) kurulmuş bir kümede etkin nesil 1'dir."""
    await put_legacy_template(search_client)

    assert await SearchIndex(search_client).active_generation() == 1


async def test_index_of_a_generation_being_built_is_not_searchable(search_client: AsyncElasticsearch) -> None:
    """Takma adsız kurulan neslin indeksi aramaya girmez; eski geniş şablon dursa bile."""
    await put_legacy_template(search_client)
    index = SearchIndex(search_client)
    await index.put_template(2, searchable=False)

    await search_client.index(index="articles-g1-2026.11.01", id="eski", document={"language": "tr"}, refresh=True)
    await search_client.index(index="articles-g2-2026.11.01", id="yeni", document={"language": "tr"}, refresh=True)

    response = await search_client.search(index=ALIAS, query={"match_all": {}})
    assert [hit["_id"] for hit in response["hits"]["hits"]] == ["eski"]


async def test_switching_moves_the_alias_and_removes_other_generations(search_client: AsyncElasticsearch) -> None:
    """Nesil değişince takma ad yeni indekslere geçer; eski neslin şablonu ve indeksleri silinir."""
    index = SearchIndex(search_client)
    await index.ensure_ready()
    await search_client.index(index="articles-g1-2026.11.01", id="eski", document={"language": "tr"}, refresh=True)
    await index.put_template(2, searchable=False)
    await search_client.index(index="articles-g2-2026.11.01", id="yeni", document={"language": "tr"}, refresh=True)

    await index.switch_to(2)

    response = await search_client.search(index=ALIAS, query={"match_all": {}})
    assert [hit["_id"] for hit in response["hits"]["hits"]] == ["yeni"]
    assert sorted((await search_client.indices.get(index="articles-*")).body) == ["articles-g2-2026.11.01"]
    templates = await search_client.indices.get_index_template(name="articles*")
    assert [template["name"] for template in templates["index_templates"]] == ["articles-g2"]
    assert await index.active_generation() == 2


async def test_month_opened_after_the_switch_joins_the_alias(search_client: AsyncElasticsearch) -> None:
    """Nesil değiştikten sonra açılan yeni aylık indeks de kendiliğinden aramaya girer."""
    index = SearchIndex(search_client)
    await index.put_template(2, searchable=False)
    await index.switch_to(2)

    await search_client.index(index="articles-g2-2026.12.01", id="aralik", document={"language": "tr"}, refresh=True)

    assert (await search_client.count(index=ALIAS))["count"] == 1
