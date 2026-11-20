"""`feeds` tablosunun sorguları. Servisler SQL görmez; SQL yalnızca buradadır."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import psycopg
from psycopg.rows import TupleRow, class_row


@dataclass(frozen=True)
class DueFeed:
    """Okuma zamanı gelmiş bir besleme; okumak için gereken kaynak ayarlarıyla birlikte."""

    id: UUID
    source_id: UUID
    source_code: str
    # Kaynağın dili (`tr`, `en`); haberlerin diline ve kategori değerlerinin küçük harfe çevrilmesine yön verir.
    language: str
    # Aynı kaynağa iki istek arasında beklenecek süre.
    request_interval_seconds: int
    # Kaynağın standart dışı etiketleri (ör. CNN Türk {"image": "image"}); yoksa None.
    field_mapping: dict[str, str] | None
    # Beslemedeki saatlerin gerçekte yazıldığı saat dilimi (ör. CNN Türk "Europe/Istanbul"); yoksa None
    # ve beslemede yazan saat dilimine güvenilir.
    feed_time_zone: str | None
    name: str
    url: str
    # Besleme düzeyindeki kategori; karışık içerikli beslemelerde None.
    default_category_code: str | None
    use_item_categories: bool
    # Koşullu istek için önceki başarılı indirmeden kalan değerler.
    etag: str | None
    last_modified: str | None
    next_fetch_at: datetime
    # Yönetici elle toplama istediyse isteğin zamanı (FG-YP-08); okuma MANUAL olarak kaydedilir.
    # Okumanın sonucu yazılırken bu değerle karşılaştırılır (bkz. _MANUAL_REQUEST_CONSUMED).
    manual_fetch_requested_at: datetime | None


@dataclass(frozen=True)
class FailureState:
    consecutive_failures: int
    enabled: bool


# Elle toplama da bu sorguyla çalışır: API beslemenin next_fetch_at değerini şimdiye çeker ve
# manual_fetch_requested_at'i doldurur, işçi bir sonraki turda onu burada bulur (ADR-0013).
_FIND_DUE_QUERY = """
    SELECT f.id, s.id AS source_id, s.code AS source_code, s.language, s.request_interval_seconds,
           s.field_mapping, s.feed_time_zone, f.name, f.url, c.code AS default_category_code, f.use_item_categories,
           f.etag, f.last_modified, f.next_fetch_at, f.manual_fetch_requested_at
    FROM feeds f
    JOIN sources s ON s.id = f.source_id
    LEFT JOIN categories c ON c.id = f.default_category_id
    WHERE f.enabled
      AND s.enabled
      AND f.next_fetch_at <= now()
    ORDER BY f.next_fetch_at, f.id
    LIMIT %(limit)s
"""

# Elle toplama isteğinin tüketilmesi (sonucu yazan dört sorguda da aynı kural):
#
#   manual_fetch_requested_at IS NOT DISTINCT FROM %(manual_requested_at)s
#
# "Sütundaki değer, okumanın başında okunan değerle aynı mı?" (ikisi de boşsa da aynı sayılır).
# - Aynıysa istek bu okumayla karşılanmıştır: sütun boşaltılır, bir sonraki okuma normal kurala göre
#   ayarlanır.
# - Farklıysa okuma sürerken yönetici yeniden istemiştir: istek kaybolmasın diye sütun kalır ve besleme
#   hemen yeniden okunur (next_fetch_at = now()). Yoksa bu sorgu, API'nin şimdiye çektiği okuma zamanını
#   ileriye iterdi.
# UPDATE'in SET kısmındaki her ifade satırın güncellenmeden önceki değerlerini görür; bu yüzden koşul iki
# sütun için de aynı sonucu verir.

# Başarılı okuma: hata sayacı sıfırlanır, bir sonraki okuma beslemenin sıklığına göre ayarlanır
# ve koşullu istek değerleri saklanır.
_RECORD_SUCCESS_QUERY = """
    UPDATE feeds
    SET next_fetch_at = CASE
            WHEN manual_fetch_requested_at IS NOT DISTINCT FROM %(manual_requested_at)s::timestamptz
            THEN now() + make_interval(mins => fetch_interval_minutes)
            ELSE now() END,
        manual_fetch_requested_at = CASE
            WHEN manual_fetch_requested_at IS NOT DISTINCT FROM %(manual_requested_at)s::timestamptz
            THEN NULL
            ELSE manual_fetch_requested_at END,
        consecutive_failures = 0,
        last_success_at = now(),
        last_error = NULL,
        etag = %(etag)s,
        last_modified = %(last_modified)s
    WHERE id = %(feed_id)s
"""

# İçerik değişmemiş (304): bu da başarılı bir okumadır; saklanan koşullu istek değerleri aynen kalır.
_RECORD_NOT_MODIFIED_QUERY = """
    UPDATE feeds
    SET next_fetch_at = CASE
            WHEN manual_fetch_requested_at IS NOT DISTINCT FROM %(manual_requested_at)s::timestamptz
            THEN now() + make_interval(mins => fetch_interval_minutes)
            ELSE now() END,
        manual_fetch_requested_at = CASE
            WHEN manual_fetch_requested_at IS NOT DISTINCT FROM %(manual_requested_at)s::timestamptz
            THEN NULL
            ELSE manual_fetch_requested_at END,
        consecutive_failures = 0,
        last_success_at = now(),
        last_error = NULL
    WHERE id = %(feed_id)s
"""

# Kaynak "çok sık geliyorsun" dedi (429): okuma ertelenir, hata sayacı artmaz. Bekleme süresi,
# beslemenin kendi sıklığı ile kaynağın istediği süreden uzun olanıdır.
_RECORD_POSTPONED_QUERY = """
    UPDATE feeds
    SET next_fetch_at = CASE
            WHEN manual_fetch_requested_at IS NOT DISTINCT FROM %(manual_requested_at)s::timestamptz
            THEN now() + greatest(
                make_interval(mins => fetch_interval_minutes),
                make_interval(secs => %(retry_after_seconds)s::double precision)
            )
            ELSE now() END,
        manual_fetch_requested_at = CASE
            WHEN manual_fetch_requested_at IS NOT DISTINCT FROM %(manual_requested_at)s::timestamptz
            THEN NULL
            ELSE manual_fetch_requested_at END,
        last_error = %(error)s
    WHERE id = %(feed_id)s
"""

# FOR UPDATE: satır bu işlem bitene kadar kilitlenir; sayaç okunup artırılırken araya
# başka bir değişiklik (örneğin yöneticinin beslemeyi elle kapatması) giremez.
_LOCK_FAILURE_STATE_QUERY = """
    SELECT consecutive_failures, enabled
    FROM feeds
    WHERE id = %(feed_id)s
    FOR UPDATE
"""

# Otomatik devre dışı bırakma yalnızca istenirse yapılır; elle kapatılmış bir beslemenin
# durumu ve nedeni değiştirilmez.
_RECORD_FAILURE_QUERY = """
    UPDATE feeds
    SET consecutive_failures = %(consecutive_failures)s,
        last_error = %(error)s,
        next_fetch_at = CASE
            WHEN manual_fetch_requested_at IS NOT DISTINCT FROM %(manual_requested_at)s::timestamptz
            THEN now() + make_interval(mins => %(retry_delay_minutes)s::integer)
            ELSE now() END,
        manual_fetch_requested_at = CASE
            WHEN manual_fetch_requested_at IS NOT DISTINCT FROM %(manual_requested_at)s::timestamptz
            THEN NULL
            ELSE manual_fetch_requested_at END,
        enabled = CASE WHEN %(disable)s::boolean THEN false ELSE enabled END,
        disabled_reason = CASE WHEN %(disable)s::boolean THEN 'AUTO' ELSE disabled_reason END
    WHERE id = %(feed_id)s
"""


class FeedRepository:
    async def find_due(self, connection: psycopg.AsyncConnection[TupleRow], limit: int) -> list[DueFeed]:
        """Etkin bir kaynağa ait, etkin ve okuma zamanı gelmiş beslemeleri en çok bekleyenden başlayarak döner."""
        # class_row: her satırı, sütun adlarını alan adlarıyla eşleştirerek DueFeed'e çevirir.
        async with connection.cursor(row_factory=class_row(DueFeed)) as cursor:
            await cursor.execute(_FIND_DUE_QUERY, {"limit": limit})
            return await cursor.fetchall()

    # Sonucu yazan dört metottaki `manual_requested_at`: okumanın başında okunan elle toplama isteğinin
    # zamanı (DueFeed.manual_fetch_requested_at); istek yoksa None.

    async def record_success(
        self,
        connection: psycopg.AsyncConnection[TupleRow],
        feed_id: UUID,
        etag: str | None,
        last_modified: str | None,
        manual_requested_at: datetime | None,
    ) -> None:
        await connection.execute(
            _RECORD_SUCCESS_QUERY,
            {
                "feed_id": feed_id,
                "etag": etag,
                "last_modified": last_modified,
                "manual_requested_at": manual_requested_at,
            },
        )

    async def record_not_modified(
        self,
        connection: psycopg.AsyncConnection[TupleRow],
        feed_id: UUID,
        manual_requested_at: datetime | None,
    ) -> None:
        await connection.execute(
            _RECORD_NOT_MODIFIED_QUERY, {"feed_id": feed_id, "manual_requested_at": manual_requested_at}
        )

    async def record_postponed(
        self,
        connection: psycopg.AsyncConnection[TupleRow],
        feed_id: UUID,
        error: str,
        retry_after_seconds: float | None,
        manual_requested_at: datetime | None,
    ) -> None:
        await connection.execute(
            _RECORD_POSTPONED_QUERY,
            {
                "feed_id": feed_id,
                "error": error,
                "retry_after_seconds": retry_after_seconds or 0,
                "manual_requested_at": manual_requested_at,
            },
        )

    async def lock_failure_state(self, connection: psycopg.AsyncConnection[TupleRow], feed_id: UUID) -> FailureState:
        """Beslemenin hata sayacını ve etkin olup olmadığını, satırı kilitleyerek okur. İşlem içinde çağrılır."""
        async with connection.cursor(row_factory=class_row(FailureState)) as cursor:
            await cursor.execute(_LOCK_FAILURE_STATE_QUERY, {"feed_id": feed_id})
            state = await cursor.fetchone()
        if state is None:
            raise LookupError(f"Besleme bulunamadı: {feed_id}")
        return state

    async def record_failure(
        self,
        connection: psycopg.AsyncConnection[TupleRow],
        feed_id: UUID,
        error: str,
        consecutive_failures: int,
        retry_delay_minutes: int,
        disable: bool,
        manual_requested_at: datetime | None,
    ) -> None:
        """Başarısız okumayı yazar. `disable` true ise besleme otomatik olarak devre dışı bırakılır."""
        await connection.execute(
            _RECORD_FAILURE_QUERY,
            {
                "feed_id": feed_id,
                "error": error,
                "consecutive_failures": consecutive_failures,
                "retry_delay_minutes": retry_delay_minutes,
                "disable": disable,
                "manual_requested_at": manual_requested_at,
            },
        )
