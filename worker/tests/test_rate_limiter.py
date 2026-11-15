import asyncio

import pytest

from news_worker.rate_limiter import SourceRateLimiter


class FakeTime:
    """Sahte saat ve sahte bekleme: beklenen süre saate eklenir, test gerçekten beklemez."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def fake_time() -> FakeTime:
    return FakeTime()


@pytest.fixture
def limiter(fake_time: FakeTime) -> SourceRateLimiter:
    return SourceRateLimiter(clock=fake_time.clock, sleep=fake_time.sleep)


async def test_first_request_to_a_source_does_not_wait(limiter: SourceRateLimiter, fake_time: FakeTime) -> None:
    """Kaynağa yapılan ilk istek bekletilmez."""
    async with limiter.request_slot("TRT", 5):
        pass

    assert fake_time.sleeps == []


async def test_second_request_waits_for_the_remaining_interval(limiter: SourceRateLimiter, fake_time: FakeTime) -> None:
    """Son istekten 2 saniye sonra gelen istek, 5 saniyelik aralığın kalan 3 saniyesi kadar bekler."""
    async with limiter.request_slot("TRT", 5):
        pass
    fake_time.now += 2

    async with limiter.request_slot("TRT", 5):
        pass

    assert fake_time.sleeps == [3]


async def test_request_does_not_wait_when_interval_has_passed(limiter: SourceRateLimiter, fake_time: FakeTime) -> None:
    """Aralık zaten geçmişse istek bekletilmez."""
    async with limiter.request_slot("TRT", 5):
        pass
    fake_time.now += 5

    async with limiter.request_slot("TRT", 5):
        pass

    assert fake_time.sleeps == []


async def test_interval_is_counted_from_the_end_of_the_previous_request(
    limiter: SourceRateLimiter, fake_time: FakeTime
) -> None:
    """Süre isteğin bitişinden sayılır: 4 saniye süren bir istekten sonra da tam 5 saniye beklenir."""
    async with limiter.request_slot("TRT", 5):
        fake_time.now += 4

    async with limiter.request_slot("TRT", 5):
        pass

    assert fake_time.sleeps == [5]


async def test_different_sources_do_not_wait_for_each_other(limiter: SourceRateLimiter, fake_time: FakeTime) -> None:
    """Sınır kaynak başınadır: bir kaynağa atılan istek başka bir kaynağı bekletmez."""
    async with limiter.request_slot("TRT", 5):
        pass

    async with limiter.request_slot("NTV", 5):
        pass

    assert fake_time.sleeps == []


async def test_each_source_uses_its_own_interval(limiter: SourceRateLimiter, fake_time: FakeTime) -> None:
    """Her kaynak kendi aralığıyla beklenir (Global Voices 10 saniye)."""
    async with limiter.request_slot("TRT", 5):
        pass
    async with limiter.request_slot("TRT", 5):
        pass

    async with limiter.request_slot("GLOBALVOICES", 10):
        pass
    async with limiter.request_slot("GLOBALVOICES", 10):
        pass

    assert fake_time.sleeps == [5, 10]


async def test_failed_request_also_counts_as_a_request(limiter: SourceRateLimiter, fake_time: FakeTime) -> None:
    """İstek hatayla bitse de kaynağa gidilmiştir; bir sonraki istek yine aralık kadar bekler."""
    with pytest.raises(RuntimeError):
        async with limiter.request_slot("TRT", 5):
            raise RuntimeError("istek başarısız")

    async with limiter.request_slot("TRT", 5):
        pass

    assert fake_time.sleeps == [5]


async def test_requests_to_same_source_run_one_at_a_time(limiter: SourceRateLimiter) -> None:
    """Aynı kaynağın istekleri sıraya girer: biri bitmeden diğeri başlamaz."""
    events: list[str] = []
    first_may_finish = asyncio.Event()

    async def first() -> None:
        async with limiter.request_slot("TRT", 5):
            events.append("birinci başladı")
            await first_may_finish.wait()
            events.append("birinci bitti")

    async def second() -> None:
        async with limiter.request_slot("TRT", 5):
            events.append("ikinci başladı")

    first_task = asyncio.create_task(first())
    await asyncio.sleep(0)
    second_task = asyncio.create_task(second())
    await asyncio.sleep(0)
    # İkinci görev çalışma fırsatı buldu ama birinci bitmediği için içeri giremedi.
    assert events == ["birinci başladı"]

    first_may_finish.set()
    await asyncio.gather(first_task, second_task)

    assert events == ["birinci başladı", "birinci bitti", "ikinci başladı"]


async def test_requests_to_different_sources_can_overlap(limiter: SourceRateLimiter) -> None:
    """Farklı kaynakların istekleri aynı anda sürebilir."""
    events: list[str] = []
    trt_may_finish = asyncio.Event()

    async def trt() -> None:
        async with limiter.request_slot("TRT", 5):
            events.append("TRT başladı")
            await trt_may_finish.wait()

    async def ntv() -> None:
        async with limiter.request_slot("NTV", 5):
            events.append("NTV başladı")

    trt_task = asyncio.create_task(trt())
    await asyncio.sleep(0)
    await asyncio.create_task(ntv())

    # TRT isteği hâlâ sürerken NTV isteği başlayıp bitti.
    assert events == ["TRT başladı", "NTV başladı"]
    trt_may_finish.set()
    await trt_task
