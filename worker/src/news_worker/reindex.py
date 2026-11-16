"""Tam yeniden indeksleme: arama indeksini PostgreSQL'den baştan üretir (ADR-0012, `05-veri-modeli.md` 5.4).

İndeks yapısı değiştiğinde (yeni bir alan, başka bir analizör) veya PostgreSQL ile Elasticsearch
arasında tutarsızlık şüphesi olduğunda elle çalıştırılır:

    news-worker-reindex

Var olan indekslere dokunulmaz; haberler yeni bir nesle yazılır ve iş bitince `articles` takma adı
oraya taşınır. Bu sayede arama, yeniden indeksleme boyunca eski indekslerden kesintisiz devam eder.

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
from news_worker.search_index import SearchIndex, create_search_client

log = logging.getLogger(__name__)

# Bir sayfada PostgreSQL'den okunup Elasticsearch'e tek istekte yazılan haber sayısı.
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
        """Bütün görünür haberleri yeni bir nesle yazar, o nesli etkin yapar ve yeni nesil numarasını döner.

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

        written = await self._copy_articles(new_generation)

        # Taşımadan önce son kontrol: yazdığımızı sandığımız kadar belge gerçekten orada mı?
        indexed = await self._search_index.count_documents(new_generation) if written else 0
        if indexed != written:
            raise ReindexError(f"Belge sayısı tutmuyor: {written} haber yazıldı, yeni nesilde {indexed} belge var")

        await self._search_index.switch_to(new_generation)
        log.info("Yeniden indeksleme bitti (etkin nesil: g%d, belge: %d)", new_generation, written)
        return new_generation

    async def _copy_articles(self, generation: int) -> int:
        """Görünür haberleri sayfa sayfa okuyup verilen nesle yazar; yazılan haber sayısını döner."""
        written = 0
        after_id = None
        async with await self._database.connect() as connection:
            while True:
                articles = await self._article_repository.find_indexable_after(connection, after_id, self._page_size)
                if not articles:
                    return written
                errors = await self._search_index.write(articles, generation)
                if errors:
                    article_id, error = next(iter(errors.items()))
                    raise ReindexError(
                        f"{len(errors)} haber yazılamadı; ilki {article_id}: {error}. Etkin nesil değişmedi"
                    )
                written += len(articles)
                after_id = articles[-1].id
                log.info("Yeniden indeksleniyor: %d haber yazıldı", written)


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
