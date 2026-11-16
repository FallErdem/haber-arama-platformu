"""Outbox aktarımı: PostgreSQL'deki notları okuyup haberleri Elasticsearch'e yazar (ADR-0012).

Her not "bu haberi arama indeksinde güncel haline getir" diye işlenir: haber duruyorsa ve gizli
değilse belgesi yazılır, aksi halde belgesi silinir. Karar, notun türüne göre değil haberin o anki
durumuna göre verildiği için bir notun geç veya iki kez işlenmesi yanlış sonuç üretmez.
"""

import asyncio
import logging
from uuid import UUID

from elasticsearch import ApiError, AsyncElasticsearch, TransportError

from news_worker.articles import ArticleRepository
from news_worker.database import Database, wait_for_stop
from news_worker.outbox import OutboxEvent, OutboxRepository
from news_worker.search_index import ALIAS, SearchIndex

log = logging.getLogger(__name__)

# Elasticsearch'in reddettiği bir belge 1, 5 ve 15 dakika sonra, ardından hep 15 dakikada bir
# yeniden denenir. Nottan vazgeçilmez: sorun (örneğin şablondaki bir eksik) düzeltildiğinde haber
# kendiliğinden aramaya girer.
RETRY_DELAYS_MINUTES = (1, 5, 15)

_MAX_ERROR_LENGTH = 500


def retry_delay_minutes(attempts: int) -> int:
    """Daha önce `attempts` kez başarısız olmuş bir notun bir sonraki denemesine kaç dakika var."""
    return RETRY_DELAYS_MINUTES[min(attempts, len(RETRY_DELAYS_MINUTES) - 1)]


class OutboxRelay:
    def __init__(
        self,
        database: Database,
        outbox_repository: OutboxRepository,
        article_repository: ArticleRepository,
        client: AsyncElasticsearch,
        search_index: SearchIndex,
        interval_seconds: float,
        batch_size: int,
    ) -> None:
        self._database = database
        self._outbox_repository = outbox_repository
        self._article_repository = article_repository
        self._client = client
        self._search_index = search_index
        self._interval_seconds = interval_seconds
        self._batch_size = batch_size

    async def relay_batch(self) -> int:
        """Bir grup notu işler ve gruptaki not sayısını döner.

        Elasticsearch'e hiç ulaşılamazsa hata fırlatır ve notlara dokunmaz: sorun notlarda değildir,
        aynı notlar bir sonraki turda yeniden denenir.
        """
        async with await self._database.connect() as connection:
            events = await self._outbox_repository.find_due(connection, self._batch_size)
            if not events:
                return 0
            # Aynı haber için birden fazla not olabilir; haber bir kez okunur ve bir kez gönderilir.
            article_ids = list({event.article_id for event in events})
            articles = await self._article_repository.find_indexable(connection, article_ids)

        errors: dict[UUID, str] = {}
        # Etkin nesil her turda Elasticsearch'e sorulur: yeniden indekslemeden sonra işçi kendiliğinden
        # yeni nesle yazar.
        generation = await self._search_index.active_generation()
        errors.update(await self._search_index.write(list(articles.values()), generation))
        # Okunamayan haber silinmiş ya da gizlenmiştir; indekste bulunmamalıdır.
        errors.update(await self._delete([article_id for article_id in article_ids if article_id not in articles]))

        await self._record_results(events, errors)
        log.info(
            "Outbox aktarıldı (not: %d, yazılan haber: %d, silinen haber: %d, hata: %d)",
            len(events),
            len(articles),
            len(article_ids) - len(articles),
            len(errors),
        )
        return len(events)

    async def run(self, stop: asyncio.Event) -> None:
        """İndeks şablonunu kurar ve durdurma istenene kadar notları aktarır."""
        index_ready = False
        while not stop.is_set():
            try:
                if not index_ready:
                    # İlk belgeden önce şablon kurulmuş olmalıdır; yoksa Elasticsearch aylık indeksi
                    # alanları tahmin ederek açar (yanlış analizör). Elasticsearch açılışta kapalıysa
                    # kurulum da aşağıdaki gibi bir sonraki turda yeniden denenir; işçi çökmez.
                    await self._search_index.ensure_ready()
                    index_ready = True
                count = await self.relay_batch()
            except (ApiError, TransportError) as error:
                # Elasticsearch kapalı veya yanıt vermiyor: notlar PostgreSQL'de bekler, bir sonraki
                # turda yeniden denenir. Beklenen bir durum olduğu için yığın izi yazılmaz.
                log.warning("Elasticsearch'e ulaşılamadı; outbox notları bekliyor: %s", error)
                count = 0
            except Exception:
                log.exception("Outbox turu başarısız oldu")
                count = 0
            # Grup dolu geldiyse bekleyen başka notlar da vardır; beklemeden devam edilir.
            if count < self._batch_size:
                await wait_for_stop(stop, self._interval_seconds)

    async def _delete(self, article_ids: list[UUID]) -> dict[UUID, str]:
        """Verilen haberlerin belgelerini siler. Belge zaten yoksa hata sayılmaz."""
        if not article_ids:
            return {}
        # Silinmiş bir haberin yayın tarihi, dolayısıyla hangi aylık indekste olduğu bilinmez; belge
        # bütün indekslerde kimliğiyle aranıp silinir. Arama yalnızca yenilenmiş (refresh) belgeleri
        # görür; az önce yazılmış bir belgenin de bulunması için önce yenileme yapılır.
        await self._client.indices.refresh(index=ALIAS, ignore_unavailable=True)
        response = await self._client.delete_by_query(
            index=ALIAS,
            query={"ids": {"values": [str(article_id) for article_id in article_ids]}},
            # Henüz hiç indeks yoksa (ilk haber yazılmadan) silinecek bir şey de yoktur.
            ignore_unavailable=True,
            conflicts="proceed",
        )
        if not response["failures"]:
            return {}
        # Hangi belgenin silinemediği ayırt edilmez; hepsi yeniden denenir (silme tekrarlanabilir).
        return dict.fromkeys(article_ids, f"Belge silinemedi: {response['failures'][0]}")

    async def _record_results(self, events: list[OutboxEvent], errors: dict[UUID, str]) -> None:
        """Sonuçları notlara yazar; hepsi tek işlemde kalıcı olur."""
        async with await self._database.connect() as connection:
            processed = [event.id for event in events if event.article_id not in errors]
            await self._outbox_repository.mark_processed(connection, processed)
            for event in events:
                error = errors.get(event.article_id)
                if error is None:
                    continue
                log.error("Haber arama indeksine aktarılamadı (haber: %s): %s", event.article_id, error)
                await self._outbox_repository.record_failure(
                    connection, event.id, error[:_MAX_ERROR_LENGTH], retry_delay_minutes(event.attempts)
                )
