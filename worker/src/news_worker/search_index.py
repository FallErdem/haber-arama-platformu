"""Elasticsearch arama indeksinin kurulumu (`05-veri-modeli.md` 5. bölüm; ADR-0011, ADR-0012).

Elasticsearch, PostgreSQL'deki haberlerin aranabilir bir kopyasını tutar. Haberler yayın tarihinin
ayına göre aylık indekslere yazılır (`articles-g1-2026.11.01`); aramalar bütün aylık indeksleri
kapsayan `articles` takma adı üzerinden yapılır.
"""

from datetime import UTC, datetime
from typing import Any

from elastic_transport import HttpxAsyncHttpNode
from elasticsearch import AsyncElasticsearch

# Aramaların yapıldığı takma ad; bütün aylık indeksleri kapsar.
ALIAS = "articles"
# İndeks nesli. Tam yeniden indeksleme yeni bir nesle (g2) yapılır ve takma ad oraya taşınır.
INDEX_GENERATION = "g1"
INDEX_PATTERN = "articles-*"
POLICY_NAME = "articles"
TEMPLATE_NAME = "articles"

# Yaşam döngüsü eşikleri indeksin yaşına göredir ve indeksin yaşı ayın ilk gününden sayılır.
# 60 günlük bir aylık indeksteki en yeni haber 30 günlük, 395 günlük indeksteki en yeni haber
# 1 yıllıktır; böylece Elasticsearch'teki aşama, PostgreSQL'deki durumdan (30 gün, 1 yıl) önce değişmez.
WARM_AFTER_DAYS = 60
COLD_AFTER_DAYS = 395

_LIFECYCLE_POLICY: dict[str, Any] = {
    "phases": {
        "hot": {"actions": {}},
        # Ilık: indeksin parçaları tek parçada birleştirilir; aramalar hızlanır. İndeks yazmaya açık kalır
        # (ADR-0015): eski tarihli bir haber sonradan da gelebilir.
        "warm": {"min_age": f"{WARM_AFTER_DAYS}d", "actions": {"forcemerge": {"max_num_segments": 1}}},
        # Soğuk: düğüm yeniden başladığında bu indeksler en son yüklenir.
        "cold": {"min_age": f"{COLD_AFTER_DAYS}d", "actions": {"set_priority": {"priority": 0}}},
    }
}


def _text(analyzer: str) -> dict[str, str]:
    return {"type": "text", "analyzer": analyzer}


# Türkçe ve İngilizce metinler ayrı alanlarda tutulur; her alan kendi dilinin analizörüyle işlenir
# (FG-AR-11). Türkçe analizör ekleri atar ve "İ/i", "I/ı" kurallarını bilir: "İstanbul'daki
# KİTAPLARI" metni "istanbul" ve "kitap" olarak indekslenir.
_MAPPINGS: dict[str, Any] = {
    # strict: burada tanımlı olmayan bir alan gönderilirse Elasticsearch belgeyi reddeder;
    # yazım hatası sessizce yeni bir alan oluşturamaz.
    "dynamic": "strict",
    "properties": {
        "source_code": {"type": "keyword"},
        "language": {"type": "keyword"},
        "item_type": {"type": "keyword"},
        "categories": {"type": "keyword"},
        "published_at": {"type": "date"},
        "group_id": {"type": "keyword"},
        "title_tr": _text("turkish"),
        "summary_tr": _text("turkish"),
        "content_tr": _text("turkish"),
        "title_en": _text("english"),
        "summary_en": _text("english"),
        "content_en": _text("english"),
    },
}


def create_search_client(url: str, username: str, password: str, request_timeout_seconds: float) -> AsyncElasticsearch:
    """Elasticsearch istemcisini kurar. Bağlantılar için projede zaten kullanılan httpx seçilir."""
    return AsyncElasticsearch(
        url,
        basic_auth=(username, password),
        # İstemcinin asyncio sürümü varsayılan olarak ayrı bir HTTP kütüphanesi (aiohttp) ister;
        # bu seçenekle projede zaten bulunan httpx kullanılır.
        node_class=HttpxAsyncHttpNode,
        request_timeout=request_timeout_seconds,
    )


def index_name_for(published_at: datetime, generation: str = INDEX_GENERATION) -> str:
    """Haberin yazılacağı aylık indeksin adı: yayın tarihinin (UTC) ayının ilk günü."""
    month = published_at.astimezone(UTC)
    return f"articles-{generation}-{month:%Y.%m}.01"


class SearchIndex:
    def __init__(self, client: AsyncElasticsearch, number_of_replicas: int = 0) -> None:
        self._client = client
        # Tek düğümlü kümede kopya tutulacak ikinci bir düğüm yoktur; 0 dışındaki bir değer
        # indeksleri "sarı" durumda bırakır.
        self._number_of_replicas = number_of_replicas

    async def ensure_ready(self) -> None:
        """Yaşam döngüsü politikasını ve indeks şablonunu oluşturur veya günceller.

        Her açılışta çağrılabilir: aynı tanım yeniden gönderildiğinde bir şey bozulmaz. Aylık indeksler
        burada oluşturulmaz; bir aya ait ilk haber yazıldığında Elasticsearch indeksi şablondaki
        ayarlarla kendisi açar.
        """
        await self._client.ilm.put_lifecycle(name=POLICY_NAME, policy=_LIFECYCLE_POLICY)
        await self._client.indices.put_index_template(
            name=TEMPLATE_NAME,
            index_patterns=[INDEX_PATTERN],
            template={
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": self._number_of_replicas,
                    "index.lifecycle.name": POLICY_NAME,
                    # İndeksin yaşı oluşturulma zamanından değil, adındaki tarihten hesaplanır;
                    # geçmiş tarihli haberlerin yazıldığı indeksler de doğru yaşta kabul edilir.
                    "index.lifecycle.parse_origination_date": True,
                },
                "mappings": _MAPPINGS,
                "aliases": {ALIAS: {}},
            },
        )
