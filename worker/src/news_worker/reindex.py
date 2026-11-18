"""Tam yeniden indeksleme: arama indeksini yeni bir nesle taşır (ADR-0012, ADR-0019, `05-veri-modeli.md` 5.4).

İndeks yapısı değiştiğinde (yeni bir alan, başka bir analizör) veya PostgreSQL ile Elasticsearch
arasında tutarsızlık şüphesi olduğunda elle çalıştırılır:

    news-worker-reindex

Haber metinlerinin (özet, tam metin, yazar) tek kaydı Elasticsearch olduğundan kaynak, etkin nesildeki
belgelerdir. PostgreSQL'deki haberler sayfa sayfa okunur; her sayfada:

1. Haberlerin belgeleri eski nesilden yeni nesle kopyalanır (Elasticsearch'in `_reindex` işlemi); yeni
   neslin şablonu uygulanır.
2. Meta veri (kategoriler, gizleme bilgisi, başlık) PostgreSQL'den belgelere yazılır; tutarsızlıklar
   giderilir. Eski nesilde belgesi olmayan bir haberin belgesi meta veriyle oluşturulur.

PostgreSQL'de olmayan (silinmiş) haberlerin belgeleri kopyalanmaz. Var olan indekslere dokunulmaz;
iş bitince `articles` takma adı yeni nesle taşınır. Bu sayede arama, yeniden indeksleme boyunca eski
indekslerden kesintisiz devam eder.

Çalışırken işçi durdurulmuş olmalıdır (kümede `scripts/dev/reindex.sh` bunu kendisi yapar): işçi
çalışsaydı, kopyalama sürerken topladığı haberleri eski nesle yazardı ve bunlar yeni nesilde eksik
kalırdı. İşçi dururken biriken outbox notları, işçi açıldığında yeni nesle işlenir.
"""

import asyncio
import logging

from news_worker.articles import ArticleRepository
from news_worker.config import ConfigurationError, Settings
from news_worker.database import Database
from news_worker.logging_config import configure_logging
from news_worker.search_index import DocumentWrite, SearchIndex, create_search_client

log = logging.getLogger(__name__)

# Bir sayfada PostgreSQL'den okunup yeni nesle taşınan haber sayısı.
PAGE_SIZE = 500


class ReindexError(Exception):
    """Yeniden indeksleme tamamlanamadı; etkin nesil değişmedi."""


class Reindexer:
    def __init__(
        self,
        database: Database,
        article_repository: ArticleRepository,
        search_index: SearchIndex,
        page_size: int = PAGE_SIZE,
    ) -> None:
        self._database = database
        self._article_repository = article_repository
        self._search_index = search_index
        self._page_size = page_size

    async def run(self) -> int:
        """Bütün haberleri yeni bir nesle taşır, o nesli etkin yapar ve yeni nesil numarasını döner.

        Bir hata olursa `ReindexError` fırlatır; o ana kadar etkin olan nesle dokunulmamıştır.
        """
        old_generation = await self._search_index.active_generation()
        new_generation = old_generation + 1
        log.info("Yeniden indeksleme başladı (etkin nesil: g%d, yeni nesil: g%d)", old_generation, new_generation)

        # Yarıda kalmış bir önceki denemenin artıkları: aramada görünmeyen, eksik indeksler.
        await self._search_index.discard_generation(new_generation)
        # Yeni neslin şablonu takma ad olmadan kurulur: indeksler dolarken aramaya girmez; yoksa her
        # haber aramada iki kez (eski ve yeni nesilde) çıkardı.
        await self._search_index.put_template(new_generation, searchable=False)

        # Eski neslin son yazılan belgeleri de kopyalanabilsin diye önce yenilenir.
        await self._search_index.refresh_generation(old_generation)
        written = await self._copy_articles(old_generation, new_generation)

        # Taşımadan önce son kontrol: yazdığımızı sandığımız kadar belge gerçekten orada mı?
        indexed = await self._search_index.count_documents(new_generation) if written else 0
        if indexed != written:
            raise ReindexError(f"Belge sayısı tutmuyor: {written} haber yazıldı, yeni nesilde {indexed} belge var")

        await self._search_index.switch_to(new_generation)
        log.info("Yeniden indeksleme bitti (etkin nesil: g%d, belge: %d)", new_generation, written)
        return new_generation

    async def _copy_articles(self, old_generation: int, new_generation: int) -> int:
        """Haberleri sayfa sayfa yeni nesle taşır; taşınan haber sayısını döner."""
        written = 0
        after_id = None
        async with await self._database.connect() as connection:
            while True:
                articles = await self._article_repository.find_metadata_after(connection, after_id, self._page_size)
                if not articles:
                    return written
                try:
                    # Belgeler metinleriyle birlikte eski nesilden kopyalanır.
                    await self._search_index.copy_documents(
                        old_generation, new_generation, [article.id for article in articles]
                    )
                except RuntimeError as error:
                    raise ReindexError(f"{error}. Etkin nesil değişmedi") from error
                # Meta veri PostgreSQL'den yazılır; metinlere dokunulmaz.
                errors = await self._search_index.write(
                    [DocumentWrite(article) for article in articles], new_generation
                )
                if errors:
                    first_id, first_error = next(iter(errors.items()))
                    raise ReindexError(
                        f"{len(errors)} haber yazılamadı; ilki {first_id}: {first_error}. Etkin nesil değişmedi"
                    )
                written += len(articles)
                after_id = articles[-1].id
                log.info("Yeniden indeksleniyor: %d haber taşındı", written)


async def run(settings: Settings) -> int:
    """Ayarlardaki PostgreSQL ve Elasticsearch ile yeniden indeksler; yeni nesil numarasını döner."""
    async with create_search_client(
        settings.es_url, settings.es_user, settings.es_password, settings.es_timeout_seconds
    ) as search_client:
        reindexer = Reindexer(Database(settings), ArticleRepository(), SearchIndex(search_client))
        return await reindexer.run()


def main() -> None:
    configure_logging()
    try:
        settings = Settings.from_environment()
    except ConfigurationError as error:
        log.error("Yapılandırma hatası: %s", error)
        raise SystemExit(2) from None
    try:
        asyncio.run(run(settings))
    except ReindexError as error:
        log.error("Yeniden indeksleme başarısız: %s", error)
        raise SystemExit(1) from None
