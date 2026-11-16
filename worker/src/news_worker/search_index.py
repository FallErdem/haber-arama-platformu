"""Elasticsearch arama indeksi: kurulum, yazma ve nesil değiştirme (`05-veri-modeli.md` 5. bölüm;
ADR-0011, ADR-0012).

Elasticsearch, PostgreSQL'deki haberlerin aranabilir bir kopyasını tutar. Haberler yayın tarihinin
ayına göre aylık indekslere yazılır (`articles-g1-2026.11.01`); aramalar etkin neslin bütün aylık
indekslerini kapsayan `articles` takma adı üzerinden yapılır.

Nesil: tam yeniden indeksleme var olan indeksleri değiştirmez; haberleri yeni bir nesle (`g2`)
baştan yazar ve bitince takma adı oraya taşır. Her neslin kendi şablonu vardır (`articles-g2`);
takma adı yalnızca etkin neslin şablonu taşır. "Hangi nesil etkin?" sorusunun cevabı bir ayarda
değil Elasticsearch'tedir: takma adı taşıyan şablonun nesli.
"""

import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from elastic_transport import HttpxAsyncHttpNode
from elasticsearch import AsyncElasticsearch, NotFoundError

from news_worker.search_document import IndexableArticle, build_document, document_id

# Aramaların yapıldığı takma ad; etkin neslin bütün aylık indekslerini kapsar.
ALIAS = "articles"
# Bütün nesillerin indeksleri.
INDEX_PATTERN = "articles-*"
POLICY_NAME = "articles"
# Hiç şablon yokken (ilk kurulum) etkin sayılan nesil.
FIRST_GENERATION = 1
# İlk sürümde tek bir şablon vardı: adı `articles`, kapsamı bütün nesiller. Böyle kurulmuş bir
# kümede bu şablon 1. nesil sayılır ve ilk yeniden indekslemede silinir.
LEGACY_TEMPLATE_NAME = "articles"
_TEMPLATE_NAME_PATTERN = re.compile(r"^articles-g(\d+)$")
# Nesil şablonları, kapsamı daha geniş olan eski şablondan (öncelik 0) önce gelir. Bir indekse
# yalnızca en yüksek öncelikli şablon uygulanır.
_TEMPLATE_PRIORITY_BASE = 100

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


# Türkçe metinlerin ikinci, "katlanmış" hali için analizör ve alt alanın adı (`title_tr.folded`).
FOLDED_ANALYZER = "turkish_folded"
FOLDED_SUBFIELD = "folded"
# Katlanmış halde kelimenin yalnızca ilk beş harfi tutulur.
FOLDED_PREFIX_LENGTH = 5

# Yerleşik `turkish` analizörü gerçek haberlerle denendiğinde üç zayıflığı görüldü (ADR-0017):
# Türkçe karaktersiz yazılan sorgu eşleşmiyor ("cumhurbaskani"), noktasız büyük I ile yazılan
# sorgu eşleşmiyor ("ISTANBUL" -> "ıstanbul") ve kök bulucu bazı kelimelerde tekil ile çoğulu
# farklı köke indiriyor ("seçim" -> "seç", "seçimler" -> "seçim"). Bu analizör aynı metni daha
# kaba ama tutarlı bir biçime çevirir:
#   apostrophe         kesme işaretinden sonrasını atar            Türkiye'nin -> Türkiye
#   turkish_lowercase  Türkçe kurallarıyla küçük harfe çevirir     İSTANBUL -> istanbul, ISTANBUL -> ıstanbul
#   asciifolding       harfleri ASCII karşılığına çevirir          ıstanbul -> istanbul, seçim -> secim, hâlâ -> hala
#   first_letters      kelimenin ilk beş harfini alır              secimler -> secim, istanbul -> istan
# Türkçe sondan eklemeli bir dildir; kelimenin başı kökü taşır. İlk beş harf, Türkçe haber
# metinlerindeki arama deneylerinde kök bulucularla benzer sonuç vermiştir (Can ve ark., 2008).
_ANALYSIS: dict[str, Any] = {
    "filter": {
        "turkish_lowercase": {"type": "lowercase", "language": "turkish"},
        "first_letters": {"type": "truncate", "length": FOLDED_PREFIX_LENGTH},
    },
    "analyzer": {
        FOLDED_ANALYZER: {
            "type": "custom",
            "tokenizer": "standard",
            "filter": ["apostrophe", "turkish_lowercase", "asciifolding", "first_letters"],
        }
    },
}


def _text(analyzer: str) -> dict[str, Any]:
    return {"type": "text", "analyzer": analyzer}


def _turkish_text() -> dict[str, Any]:
    """Türkçe metin alanı: asıl hali `turkish` analizörüyle, alt alanı katlanmış analizörle işlenir.

    Alt alan belgeye ayrıca yazılmaz; Elasticsearch aynı metni iki biçimde indeksler. Arama iki
    alana birlikte bakar ve asıl alana daha yüksek ağırlık verir; katlanmış alan yalnızca asıl
    alanın kaçırdıklarını yakalar.
    """
    return {**_text("turkish"), "fields": {FOLDED_SUBFIELD: _text(FOLDED_ANALYZER)}}


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
        "title_tr": _turkish_text(),
        "summary_tr": _turkish_text(),
        "content_tr": _turkish_text(),
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
        # İstemci başarısız isteği kendiliğinden yeniden denemez; yeniden denemeyi, notları
        # PostgreSQL'de bekleten outbox döngüsü yapar.
        max_retries=0,
        request_timeout=request_timeout_seconds,
    )


def template_name_for(generation: int) -> str:
    return f"articles-g{generation}"


def index_pattern_for(generation: int) -> str:
    """Bir neslin bütün aylık indeksleri."""
    return f"articles-g{generation}-*"


def index_name_for(published_at: datetime, generation: int = FIRST_GENERATION) -> str:
    """Haberin yazılacağı aylık indeksin adı: yayın tarihinin (UTC) ayının ilk günü."""
    month = published_at.astimezone(UTC)
    return f"articles-g{generation}-{month:%Y.%m}.01"


class SearchIndex:
    def __init__(self, client: AsyncElasticsearch, number_of_replicas: int = 0) -> None:
        self._client = client
        # Tek düğümlü kümede kopya tutulacak ikinci bir düğüm yoktur; 0 dışındaki bir değer
        # indeksleri "sarı" durumda bırakır.
        self._number_of_replicas = number_of_replicas

    async def active_generation(self) -> int:
        """Etkin nesil: takma adı taşıyan şablonun nesli. Hiç şablon yoksa ilk nesil."""
        generations = [
            generation
            for name, template in (await self._templates()).items()
            if ALIAS in template.get("template", {}).get("aliases", {})
            and (generation := _generation_of(name)) is not None
        ]
        # Yarıda kalmış bir nesil değişiminde takma adı iki şablon taşıyabilir; yenisi geçerlidir.
        return max(generations, default=FIRST_GENERATION)

    async def ensure_ready(self) -> None:
        """Yaşam döngüsü politikasını ve etkin neslin şablonunu oluşturur veya günceller.

        Her açılışta çağrılabilir: aynı tanım yeniden gönderildiğinde bir şey bozulmaz. Aylık indeksler
        burada oluşturulmaz; bir aya ait ilk haber yazıldığında Elasticsearch indeksi şablondaki
        ayarlarla kendisi açar.
        """
        await self._client.ilm.put_lifecycle(name=POLICY_NAME, policy=_LIFECYCLE_POLICY)
        await self.put_template(await self.active_generation(), searchable=True)

    async def put_template(self, generation: int, searchable: bool) -> None:
        """Bir neslin şablonunu kurar. `searchable` ise o neslin indeksleri açılırken takma ada girer."""
        await self._client.indices.put_index_template(
            name=template_name_for(generation),
            index_patterns=[index_pattern_for(generation)],
            priority=_TEMPLATE_PRIORITY_BASE + generation,
            template={
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": self._number_of_replicas,
                    "index.lifecycle.name": POLICY_NAME,
                    # İndeksin yaşı oluşturulma zamanından değil, adındaki tarihten hesaplanır;
                    # geçmiş tarihli haberlerin yazıldığı indeksler de doğru yaşta kabul edilir.
                    "index.lifecycle.parse_origination_date": True,
                    "analysis": _ANALYSIS,
                },
                "mappings": _MAPPINGS,
                "aliases": {ALIAS: {}} if searchable else {},
            },
        )

    async def write(self, articles: list[IndexableArticle], generation: int) -> dict[UUID, str]:
        """Belgeleri tek bir toplu istekle yazar; Elasticsearch'in reddettiklerini hatasıyla döner."""
        if not articles:
            return {}
        # Toplu istek (bulk) satır çiftlerinden oluşur: önce "hangi indekse, hangi kimlikle", sonra belge.
        operations: list[dict[str, Any]] = []
        for article in articles:
            index = index_name_for(article.published_at, generation)
            operations.append({"index": {"_index": index, "_id": document_id(article)}})
            operations.append(build_document(article))
        response = await self._client.bulk(operations=operations)

        # İstek başarılı dönse de içindeki belgeler tek tek reddedilmiş olabilir; her birinin sonucuna bakılır.
        errors: dict[UUID, str] = {}
        for item in response["items"]:
            result = item["index"]
            if "error" in result:
                errors[UUID(result["_id"])] = f"{result['error']['type']}: {result['error']['reason']}"
        return errors

    async def count_documents(self, generation: int) -> int:
        """Bir neslin indekslerindeki belge sayısı. Az önce yazılanların da sayılması için önce yenilenir."""
        pattern = index_pattern_for(generation)
        await self._client.indices.refresh(index=pattern)
        response = await self._client.count(index=pattern)
        count: int = response["count"]
        return count

    async def discard_generation(self, generation: int) -> None:
        """Bir neslin indekslerini siler; yarıda kalmış bir yeniden indekslemenin artıkları içindir."""
        await self._delete_indices(await self._index_names(index_pattern_for(generation)))

    async def switch_to(self, generation: int) -> None:
        """Verilen nesli etkin yapar ve diğer nesilleri siler.

        Sıra, yarıda kesilirse yeniden çalıştırılarak tamamlanabilecek şekildedir:
        1. Yeni neslin şablonuna takma ad eklenir: bundan sonra açılan aylık indeksler aramaya girer
           ve işçi bu nesle yazar.
        2. Takma ad tek istekte eski indekslerden kaldırılıp yeni indekslere eklenir; arama hiçbir an
           boş ya da çift sonuç görmez.
        3. Diğer nesillerin şablonları ve indeksleri silinir.
        """
        await self.put_template(generation, searchable=True)

        new_indices = await self._index_names(index_pattern_for(generation))
        other_indices = [name for name in await self._index_names(INDEX_PATTERN) if name not in new_indices]
        actions: list[dict[str, Any]] = [{"add": {"index": name, "alias": ALIAS}} for name in new_indices]
        # must_exist=False: takma adı zaten taşımayan bir indeks (yarıda kalmış bir değişim) hata sayılmaz.
        actions += [{"remove": {"index": name, "alias": ALIAS, "must_exist": False}} for name in other_indices]
        if actions:
            await self._client.indices.update_aliases(actions=actions)

        for name in await self._templates():
            if name != template_name_for(generation):
                await self._client.indices.delete_index_template(name=name)
        await self._delete_indices(other_indices)

    async def _templates(self) -> dict[str, dict[str, Any]]:
        """Bu uygulamanın şablonları (eski tek şablon dahil), adlarına göre."""
        try:
            response = await self._client.indices.get_index_template(name=f"{LEGACY_TEMPLATE_NAME}*")
        except NotFoundError:
            return {}
        return {
            item["name"]: item["index_template"]
            for item in response["index_templates"]
            if item["name"] == LEGACY_TEMPLATE_NAME or _TEMPLATE_NAME_PATTERN.match(item["name"])
        }

    async def _index_names(self, pattern: str) -> list[str]:
        # expand_wildcards=all: kapatılmış indeksler de listelenir.
        response = await self._client.indices.get(index=pattern, expand_wildcards="all")
        return sorted(response.body)

    async def _delete_indices(self, names: list[str]) -> None:
        # Elasticsearch joker karakterle silmeye izin vermez; indeksler adlarıyla, gruplar halinde silinir
        # (adların hepsi tek bir adrese sığmayabilir).
        for start in range(0, len(names), _DELETE_BATCH_SIZE):
            await self._client.indices.delete(index=",".join(names[start : start + _DELETE_BATCH_SIZE]))


_DELETE_BATCH_SIZE = 50


def _generation_of(template_name: str) -> int | None:
    """Şablon adından nesil numarası; eski tek şablon 1. nesildir."""
    if template_name == LEGACY_TEMPLATE_NAME:
        return FIRST_GENERATION
    match = _TEMPLATE_NAME_PATTERN.match(template_name)
    return int(match.group(1)) if match else None
