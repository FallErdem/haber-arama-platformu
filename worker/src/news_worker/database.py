"""PostgreSQL bağlantısı ve tabloların hazır olmasını bekleme."""

import asyncio
import logging

import psycopg
from psycopg.rows import TupleRow

from news_worker.config import Settings

log = logging.getLogger(__name__)

# Tablo yoksa hata vermeden false döner; varsa işçinin okuma yetkisine bakar.
# Yetkiler V9 betiğinde verildiği için true, şemanın V9'a kadar kurulduğunu gösterir.
_SCHEMA_READY_QUERY = """
    SELECT CASE
        WHEN to_regclass('public.feeds') IS NULL THEN false
        ELSE has_table_privilege(to_regclass('public.feeds'), 'SELECT')
    END
"""


class Database:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def connect(self) -> psycopg.AsyncConnection[TupleRow]:
        """Yeni bir bağlantı açar. Çağıran `async with` ile kullanır; blok bitince bağlantı kapanır."""
        return await psycopg.AsyncConnection.connect(
            host=self._settings.db_host,
            port=self._settings.db_port,
            dbname=self._settings.db_name,
            user=self._settings.db_user,
            password=self._settings.db_password,
            connect_timeout=5,
            # pg_stat_activity'de bağlantının kime ait olduğu görünür.
            application_name="news-worker",
        )

    async def is_schema_ready(self) -> bool:
        try:
            async with await self.connect() as connection:
                cursor = await connection.execute(_SCHEMA_READY_QUERY)
                row = await cursor.fetchone()
                return row is not None and row[0] is True
        except psycopg.OperationalError as error:
            # Veritabanına ulaşılamıyor veya giriş reddedildi; neden görünür olsun.
            log.warning("Veritabanına bağlanılamadı: %s", str(error).strip())
            return False

    async def wait_until_ready(
        self,
        stop: asyncio.Event,
        retry_delay_seconds: float = 2.0,
        timeout_seconds: float | None = None,
    ) -> None:
        """Tablolar hazır olana veya durdurma istenene kadar bekler.

        Şemayı Spring Boot API kurar (ADR-0018). İşçi ondan önce başlarsa çökmek
        yerine bekler. `timeout_seconds` verilirse süre dolunca TimeoutError fırlatır.
        """
        async with asyncio.timeout(timeout_seconds):
            while not stop.is_set():
                if await self.is_schema_ready():
                    return
                log.info("Tablolar henüz hazır değil; %.0f saniye sonra yeniden denenecek", retry_delay_seconds)
                await wait_for_stop(stop, retry_delay_seconds)


async def wait_for_stop(stop: asyncio.Event, seconds: float) -> None:
    """En fazla `seconds` kadar bekler; durdurma istenirse hemen döner."""
    try:
        async with asyncio.timeout(seconds):
            await stop.wait()
    except TimeoutError:
        pass
