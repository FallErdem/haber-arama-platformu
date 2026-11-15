"""Kaynak başına ortak istek sınırlayıcısı (ADR-0013, 3. bölüm; FG-VT-05).

Aynı kaynağa atılan iki istek arasında, kaynak için tanımlı süre (`sources.request_interval_seconds`)
kadar beklenir. Sınırlayıcı "ortak"tır: bir kaynağa istek atan her iş (besleme okuma, ileride
görsel indirme) aynı nesneyi kullanır; böylece toplam istek sıklığı sınırı aşmaz.
"""

import asyncio
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager


class SourceRateLimiter:
    def __init__(
        self,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        # Testlerde sahte saat ve sahte bekleme verilir; testler gerçekten saniyelerce beklemez.
        self._clock = clock
        self._sleep = sleep
        # Her kaynağın kendi kilidi vardır: aynı kaynağın istekleri sıraya girer,
        # farklı kaynakların istekleri birbirini beklemez.
        self._locks: dict[str, asyncio.Lock] = {}
        self._last_request_finished_at: dict[str, float] = {}

    @asynccontextmanager
    async def request_slot(self, source_code: str, interval_seconds: float) -> AsyncIterator[None]:
        """Kaynağa istek atma sırasını verir. İstek `async with` bloğunun içinde atılır.

        Bloğa girmeden önce, kaynağa yapılan son isteğin bitişinden bu yana `interval_seconds`
        geçmemişse kalan süre kadar beklenir. Blok bitene kadar aynı kaynağa başka istek atılamaz.
        """
        lock = self._locks.setdefault(source_code, asyncio.Lock())
        async with lock:
            last_finished_at = self._last_request_finished_at.get(source_code)
            if last_finished_at is not None:
                remaining = interval_seconds - (self._clock() - last_finished_at)
                if remaining > 0:
                    await self._sleep(remaining)
            try:
                yield
            finally:
                # Süre isteğin bitişinden sayılır: yavaş bir yanıt, bir sonraki isteği öne çekmez.
                # İstek hatayla bitse de kaydedilir; başarısız istek de kaynağa yapılmış bir istektir.
                self._last_request_finished_at[source_code] = self._clock()
