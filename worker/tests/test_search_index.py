"""Arama indeksi kurulumunun testleri.

Elasticsearch gerçektir (kümedekiyle aynı sürüm, geçici konteyner) ve testler işçinin kendi
kullanıcısıyla, onun yetkileriyle çalışır.
"""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from elasticsearch import AsyncElasticsearch, BadRequestError

from news_worker.search_index import (
    ALIAS,
    COLD_AFTER_DAYS,
    POLICY_NAME,
    TEMPLATE_NAME,
    WARM_AFTER_DAYS,
    SearchIndex,
    index_name_for,
)

NOVEMBER_INDEX = "articles-g1-2026.11.01"


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
    assert index_name_for(datetime(2026, 11, 13, tzinfo=UTC), generation="g2") == "articles-g2-2026.11.01"


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
    templates = await search_client.indices.get_index_template(name=TEMPLATE_NAME)
    assert len(templates["index_templates"]) == 1


async def test_monthly_index_is_created_from_template_on_first_write(search_client: AsyncElasticsearch) -> None:
    """Aylık indeks elle oluşturulmaz: ilk belge yazıldığında şablondaki alanlar ve analizörlerle açılır."""
    await SearchIndex(search_client).ensure_ready()

    await search_client.index(index=NOVEMBER_INDEX, id="haber-1", document={"language": "tr"})

    mapping = await search_client.indices.get_mapping(index=NOVEMBER_INDEX)
    properties = mapping[NOVEMBER_INDEX]["mappings"]["properties"]
    assert properties["title_tr"] == {"type": "text", "analyzer": "turkish"}
    assert properties["content_tr"] == {"type": "text", "analyzer": "turkish"}
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
