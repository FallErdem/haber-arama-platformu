"""Hacim testi için deneme haberleri üretir (FOG-07, İ-35).

Deneme haberleri gerçek haberlerle aynı yoldan kaydedilir (`ArticleRepository.insert_if_new`): haber,
kategorisi ve metnini taşıyan outbox notu tek işlemde yazılır; outbox aktarımı onları Elasticsearch'e
yazar. Metinler, gerçek haberlerin Elasticsearch'teki metinlerinden çıkarılan kelime dağılımına ve ortalama
uzunluklarına göre üretilir; arama gerçekçi bir kelime dağılımıyla zorlanır.

Deneme verisi gerçek veriden ayrıdır ve işaretlidir (R-26):
- Bütün haberler yönetim panelinden oluşturulmuş, kapalı bir kaynağa (varsayılan `DENEME`) ve onun
  beslemesine aittir. Kaynak kapalı olduğu için işçi onu okumaz. İş bitince kaynağın içeriği yönetim
  panelinden silinir (FG-YP-14).
- Haber adresleri, hiçbir zaman gerçek olmayacak şekilde ayrılmış `.invalid` alan adındadır.

Kümede askıdaki CronJob'dan elle başlatılır (`deploy/k8s/base/worker/volume-data-cronjob.yaml`):

    kubectl create job -n haber --from=cronjob/worker-volume-data worker-volume-data-1

Yarıda kalırsa aynı komut yeniden çalıştırılır: aynı sıra numaralı haberler zaten kayıtlı olduğundan
atlanır, kalanlar eklenir.
"""

import argparse
import asyncio
import logging
import random
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import accumulate
from typing import Any
from uuid import UUID

import psycopg
from elasticsearch import AsyncElasticsearch
from psycopg.rows import TupleRow, class_row

from news_worker.articles import ArticleRepository, NewArticle
from news_worker.category_resolver import AssignedCategory, MappingLevel
from news_worker.config import ConfigurationError, Settings
from news_worker.database import Database
from news_worker.logging_config import configure_logging
from news_worker.parsed_article import ItemType, ParsedArticle
from news_worker.search_index import ALIAS, create_search_client
from news_worker.url_normalizer import normalize_url

log = logging.getLogger(__name__)

DEFAULT_COUNT = 1_000_000
DEFAULT_SOURCE_CODE = "DENEME"
# Aynı tohum aynı haberleri üretir; yarıda kalan bir çalışma yeniden başlatıldığında aynı sırayı izler.
DEFAULT_SEED = 42
# Bir işlemde (commit) yazılan haber sayısı. Her haber kendi işleminde yazılsaydı 1 milyon commit olurdu.
DEFAULT_BATCH_SIZE = 1000
# Kelime dağılımı için okunan gerçek haber sayısı.
SAMPLE_SIZE = 3000
# Haberlerin yayın tarihleri bu kadar güne yayılır: sıcak, ılık ve soğuk haberler birlikte bulunur (ADR-0011).
PUBLISHED_WITHIN_DAYS = 730
# Haberlerin İngilizce olanlarının oranı; kalanı Türkçe.
ENGLISH_RATIO = 0.1
LANGUAGES = ("tr", "en")
URL_PREFIX = "https://deneme.invalid/haber/"

_HTML_TAG = re.compile(r"<[^>]+>")
# Yalnızca harflerden oluşan kelimeler (Türkçe harfler dahil); sayılar ve noktalama alınmaz.
_WORD = re.compile(r"[^\W\d_]+")
_SENTENCE_WORDS = (8, 16)
_PARAGRAPH_SENTENCES = (2, 4)


class VolumeDataError(Exception):
    """Deneme verisi üretilemez; nedeni mesajdadır."""


@dataclass(frozen=True)
class TextSample:
    """Gerçek bir haberin metinleri (Elasticsearch'teki belgeden)."""

    language: str
    title: str | None
    summary: str | None
    content: str | None


def _words(text: str | None) -> list[str]:
    if not text:
        return []
    return _WORD.findall(_HTML_TAG.sub(" ", text))


def _average(lengths: list[int]) -> int:
    return round(sum(lengths) / len(lengths)) if lengths else 0


@dataclass(frozen=True)
class LanguageProfile:
    """Bir dildeki gerçek haberlerin kelimeleri (sıklıklarıyla) ve metin uzunlukları."""

    words: tuple[str, ...]
    # Kümülatif sıklıklar: kelime seçimi her seferinde bütün listeyi toplamadan, ikili aramayla yapılır.
    cumulative_weights: tuple[int, ...]
    title_words: int
    summary_words: int
    content_words: int
    # Özeti ve tam metni olan haberlerin oranı: bazı kaynaklar tam metin vermez.
    summary_ratio: float
    content_ratio: float

    @classmethod
    def from_samples(cls, samples: Sequence[TextSample]) -> LanguageProfile:
        counter: Counter[str] = Counter()
        titles: list[int] = []
        summaries: list[int] = []
        contents: list[int] = []
        for sample in samples:
            for text, lengths in ((sample.title, titles), (sample.summary, summaries), (sample.content, contents)):
                words = _words(text)
                if words:
                    counter.update(words)
                    lengths.append(len(words))
        if not counter:
            raise VolumeDataError("Örnek haberlerde kelime bulunamadı")
        common = counter.most_common()
        return cls(
            words=tuple(word for word, _ in common),
            cumulative_weights=tuple(accumulate(count for _, count in common)),
            title_words=_average(titles),
            summary_words=_average(summaries),
            content_words=_average(contents),
            summary_ratio=len(summaries) / len(samples),
            content_ratio=len(contents) / len(samples),
        )


class TextGenerator:
    """Bir dilin kelime dağılımından başlık, özet ve tam metin üretir."""

    def __init__(self, profile: LanguageProfile, rng: random.Random) -> None:
        self._profile = profile
        self._rng = rng

    def title(self) -> str:
        return self._sentence(self._length(self._profile.title_words), end="")

    def summary(self) -> str | None:
        if self._rng.random() >= self._profile.summary_ratio:
            return None
        return self._text(self._length(self._profile.summary_words))

    def content(self) -> str | None:
        """Gerçek haberlerdeki gibi temizlenmiş HTML: paragraflar."""
        if self._rng.random() >= self._profile.content_ratio:
            return None
        remaining = self._length(self._profile.content_words)
        paragraphs = []
        while remaining > 0:
            words = min(remaining, self._rng.randint(*_PARAGRAPH_SENTENCES) * self._rng.randint(*_SENTENCE_WORDS))
            paragraphs.append(f"<p>{self._text(words)}</p>")
            remaining -= words
        return "".join(paragraphs)

    def _length(self, average: int) -> int:
        """Ortalamanın yarısı ile bir buçuk katı arasında bir uzunluk (en az 1 kelime)."""
        return max(1, self._rng.randint(average // 2, average + average // 2))

    def _text(self, word_count: int) -> str:
        sentences = []
        while word_count > 0:
            length = min(word_count, self._rng.randint(*_SENTENCE_WORDS))
            sentences.append(self._sentence(length, end="."))
            word_count -= length
        return " ".join(sentences)

    def _sentence(self, word_count: int, end: str) -> str:
        words = self._rng.choices(self._profile.words, cum_weights=self._profile.cumulative_weights, k=word_count)
        sentence = " ".join(words)
        return sentence[:1].upper() + sentence[1:] + end


async def load_samples(client: AsyncElasticsearch, size: int = SAMPLE_SIZE, index: str = ALIAS) -> list[TextSample]:
    """Gerçek haberlerin metinlerini Elasticsearch'ten, her dilden `size` habere kadar okur.

    Diller ayrı ayrı istenir: İngilizce haberler azdır (yalnızca Global Voices) ve dil ayırmadan istenen bir
    örneğe hiç girmeyebilirler.
    """
    samples = []
    for language in LANGUAGES:
        response = await client.search(
            index=index,
            size=size,
            query={"term": {"language": language}},
            source_includes=[f"title_{language}", f"summary_{language}", f"content_{language}"],
        )
        for hit in response["hits"]["hits"]:
            document: dict[str, Any] = hit["_source"]
            samples.append(
                TextSample(
                    language=language,
                    title=document.get(f"title_{language}"),
                    summary=document.get(f"summary_{language}"),
                    content=document.get(f"content_{language}"),
                )
            )
    return samples


def build_profiles(samples: Iterable[TextSample]) -> dict[str, LanguageProfile]:
    by_language: dict[str, list[TextSample]] = {}
    for sample in samples:
        by_language.setdefault(sample.language, []).append(sample)
    missing = set(LANGUAGES) - by_language.keys()
    if missing:
        raise VolumeDataError(f"Örnek haberlerde şu dillerde haber yok: {', '.join(sorted(missing))}")
    return {language: LanguageProfile.from_samples(items) for language, items in by_language.items()}


@dataclass(frozen=True)
class TargetSource:
    source_id: UUID
    enabled: bool
    feed_id: UUID | None


# Deneme kaynağı ve ilk beslemesi.
_FIND_TARGET_QUERY = """
    SELECT s.id AS source_id, s.enabled,
           (SELECT f.id FROM feeds f WHERE f.source_id = s.id ORDER BY f.created_at, f.id LIMIT 1) AS feed_id
    FROM sources s
    WHERE s.code = %(code)s
"""

# Deneme haberlerine atanacak kategoriler, gerçek haberlerdeki sıklıklarıyla.
_CATEGORY_WEIGHTS_QUERY = """
    SELECT c.code, count(*)
    FROM article_categories ac
    JOIN categories c ON c.id = ac.category_id
    JOIN articles a ON a.id = ac.article_id
    JOIN sources s ON s.id = a.source_id
    WHERE s.code <> %(code)s
    GROUP BY c.code
    ORDER BY c.code
"""


class VolumeDataRepository:
    async def find_target(self, connection: psycopg.AsyncConnection[TupleRow], code: str) -> TargetSource | None:
        async with connection.cursor(row_factory=class_row(TargetSource)) as cursor:
            await cursor.execute(_FIND_TARGET_QUERY, {"code": code})
            return await cursor.fetchone()

    async def category_weights(self, connection: psycopg.AsyncConnection[TupleRow], code: str) -> dict[str, int]:
        cursor = await connection.execute(_CATEGORY_WEIGHTS_QUERY, {"code": code})
        return {category_code: count for category_code, count in await cursor.fetchall()}


@dataclass(frozen=True)
class GenerationResult:
    inserted: int
    skipped: int


class VolumeDataGenerator:
    def __init__(
        self,
        database: Database,
        repository: VolumeDataRepository,
        article_repository: ArticleRepository,
        profiles: dict[str, LanguageProfile],
        seed: int = DEFAULT_SEED,
        batch_size: int = DEFAULT_BATCH_SIZE,
        now: datetime | None = None,
    ) -> None:
        self._database = database
        self._repository = repository
        self._article_repository = article_repository
        self._profiles = profiles
        self._seed = seed
        self._batch_size = batch_size
        # Testlerde sabit bir zaman verilebilir.
        self._now = now or datetime.now(UTC)

    async def run(self, count: int, source_code: str) -> GenerationResult:
        """`count` deneme haberi üretir; sıra numarası daha önce kaydedilmiş olanları atlar."""
        rng = random.Random(self._seed)
        generators = {language: TextGenerator(profile, rng) for language, profile in self._profiles.items()}
        inserted = skipped = 0
        async with await self._database.connect() as connection:
            source_id, feed_id = await self._find_target(connection, source_code)
            weights = await self._repository.category_weights(connection, source_code)
            if not weights:
                raise VolumeDataError("Gerçek haberlerde kategori bulunamadı")
            categories = list(weights)
            cumulative = list(accumulate(weights.values()))

            for start in range(0, count, self._batch_size):
                end = min(start + self._batch_size, count)
                # Grubun bütün haberleri tek işlemde yazılır; insert_if_new'in kendi işlemi bunun içinde bir
                # kayıt noktası (savepoint) olur.
                async with connection.transaction():
                    for number in range(start, end):
                        language = "en" if rng.random() < ENGLISH_RATIO else "tr"
                        category = rng.choices(categories, cum_weights=cumulative)[0]
                        new_article = NewArticle(
                            source_id=source_id,
                            feed_id=feed_id,
                            language=language,
                            article=self._article(number, generators[language], rng),
                            categories=(AssignedCategory(category, MappingLevel.ITEM),),
                            fetched_at=self._now,
                        )
                        if await self._article_repository.insert_if_new(connection, new_article):
                            inserted += 1
                        else:
                            skipped += 1
                log.info("Deneme verisi: %d / %d haber (eklenen: %d, atlanan: %d)", end, count, inserted, skipped)
        return GenerationResult(inserted=inserted, skipped=skipped)

    async def _find_target(self, connection: psycopg.AsyncConnection[TupleRow], source_code: str) -> tuple[UUID, UUID]:
        """Deneme kaynağının ve beslemesinin kimlikleri; kaynak yoksa, açıksa veya beslemesi yoksa hata."""
        target = await self._repository.find_target(connection, source_code)
        if target is None:
            raise VolumeDataError(f"{source_code} kaynağı yok; önce yönetim panelinden oluşturulmalı")
        if target.enabled:
            # Açık kaynağı işçi okur ve içeriği silinemez (FG-YP-14); deneme verisi kapalı kaynağa yazılır.
            raise VolumeDataError(f"{source_code} kaynağı açık; önce yönetim panelinden kapatılmalı")
        if target.feed_id is None:
            raise VolumeDataError(f"{source_code} kaynağının beslemesi yok; önce yönetim panelinden eklenmeli")
        return target.source_id, target.feed_id

    def _article(self, number: int, generator: TextGenerator, rng: random.Random) -> ParsedArticle:
        url = f"{URL_PREFIX}{number}"
        published_at = self._now - timedelta(seconds=rng.uniform(0, PUBLISHED_WITHIN_DAYS * 24 * 60 * 60))
        return ParsedArticle(
            external_id=f"deneme-{number}",
            url=url,
            normalized_url=normalize_url(url),
            title=generator.title(),
            summary=generator.summary(),
            content=generator.content(),
            author=None,
            published_at=published_at,
            item_type=ItemType.ARTICLE,
            image_urls=(),
            source_categories=(),
        )


async def run(settings: Settings, count: int, source_code: str, seed: int) -> GenerationResult:
    async with create_search_client(
        settings.es_url, settings.es_user, settings.es_password, settings.es_timeout_seconds
    ) as search_client:
        profiles = build_profiles(await load_samples(search_client))
    generator = VolumeDataGenerator(
        Database(settings), VolumeDataRepository(), ArticleRepository(), profiles, seed=seed
    )
    return await generator.run(count, source_code)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Hacim testi için deneme haberleri üretir.")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help="Üretilecek haber sayısı")
    parser.add_argument("--source-code", default=DEFAULT_SOURCE_CODE, help="Haberlerin yazılacağı kapalı kaynak")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Rastgele sayı üretecinin tohumu")
    arguments = parser.parse_args(argv)

    configure_logging()
    try:
        settings = Settings.from_environment()
    except ConfigurationError as error:
        log.error("Yapılandırma hatası: %s", error)
        raise SystemExit(2) from None
    try:
        result = asyncio.run(run(settings, arguments.count, arguments.source_code, arguments.seed))
    except VolumeDataError as error:
        log.error("Deneme verisi üretilemedi: %s", error)
        raise SystemExit(1) from None
    log.info("Deneme verisi üretildi (eklenen: %d, atlanan: %d)", result.inserted, result.skipped)
