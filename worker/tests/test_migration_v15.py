"""V15 geçiş betiği: kaynağın saat dilimi ayarı ve CNN Türk'ün eski haberlerinin yayın saatinin düzeltilmesi.

CNN Türk saati Türkiye saatiyle yazıp yanına "GMT" koyduğu için haberleri 3 saat ileri kaydedilmişti.
Betik saatleri düzeltir ve arama indeksindeki belgelerin de güncellenmesi için outbox notu yazar.
"""

from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID

import psycopg
import pytest
from conftest import admin_connect, apply_migrations
from testcontainers.community.postgres import PostgresContainer

DATABASE = "migration_v15"


@pytest.fixture
def before_v15(postgres: PostgresContainer) -> Iterator[psycopg.Connection]:
    """V14'e kadar kurulmuş ayrı bir veritabanına süper kullanıcı bağlantısı; test bitince silinir."""
    with admin_connect(postgres) as admin:
        admin.execute(f"CREATE DATABASE {DATABASE} OWNER news_owner")
    try:
        apply_migrations(postgres, DATABASE, to_version=14)
        with admin_connect(postgres, DATABASE) as connection:
            yield connection
    finally:
        with admin_connect(postgres) as admin:
            admin.execute(f"DROP DATABASE {DATABASE} WITH (FORCE)")


def insert_article(connection: psycopg.Connection, source_code: str, published_at: datetime) -> UUID:
    key = f"{source_code}-{published_at.isoformat()}"
    row = connection.execute(
        """
        INSERT INTO articles (source_id, external_id, url, normalized_url, title, language, item_type,
                              published_at, fetched_at, lifecycle_state)
        SELECT id, %(key)s, %(url)s, %(url)s, %(key)s, language, 'ARTICLE', %(published_at)s, now(), 'HOT'
        FROM sources WHERE code = %(source)s
        RETURNING id
        """,
        {"key": key, "url": f"https://example.test/{key}", "published_at": published_at, "source": source_code},
    ).fetchone()
    assert row is not None
    article_id: UUID = row[0]
    return article_id


def published_at_of(connection: psycopg.Connection, article_id: UUID) -> datetime:
    row = connection.execute("SELECT published_at FROM articles WHERE id = %s", (article_id,)).fetchone()
    assert row is not None
    published_at: datetime = row[0]
    return published_at.astimezone(UTC)


def pending_notes(connection: psycopg.Connection) -> list[tuple[UUID, str]]:
    return connection.execute(
        "SELECT article_id, operation FROM outbox_events WHERE status = 'PENDING' ORDER BY article_id"
    ).fetchall()


def apply_v15(postgres: PostgresContainer) -> None:
    apply_migrations(postgres, DATABASE, from_version=15, to_version=15)


def test_cnnturk_times_are_read_as_turkey_time(postgres: PostgresContainer, before_v15: psycopg.Connection) -> None:
    # Beslemede "16:28:48 GMT" yazıyordu ve öyle kaydedildi; gerçekte Türkiye saatiydi (13:28:48 UTC).
    cnnturk = insert_article(before_v15, "CNNTURK", datetime(2026, 11, 13, 16, 28, 48, tzinfo=UTC))

    apply_v15(postgres)

    assert published_at_of(before_v15, cnnturk) == datetime(2026, 11, 13, 13, 28, 48, tzinfo=UTC)


def test_other_sources_are_not_changed(postgres: PostgresContainer, before_v15: psycopg.Connection) -> None:
    trt = insert_article(before_v15, "TRT", datetime(2026, 11, 13, 13, 40, tzinfo=UTC))

    apply_v15(postgres)

    assert published_at_of(before_v15, trt) == datetime(2026, 11, 13, 13, 40, tzinfo=UTC)
    assert pending_notes(before_v15) == []


def test_corrected_articles_get_an_index_note(postgres: PostgresContainer, before_v15: psycopg.Connection) -> None:
    """Arama indeksindeki belgenin yayın tarihi de değişmeli; işçi notu işleyince belge güncellenir."""
    cnnturk = insert_article(before_v15, "CNNTURK", datetime(2026, 11, 13, 16, 28, 48, tzinfo=UTC))

    apply_v15(postgres)

    assert pending_notes(before_v15) == [(cnnturk, "INDEX")]


def test_only_cnnturk_gets_a_feed_time_zone(postgres: PostgresContainer, before_v15: psycopg.Connection) -> None:
    apply_v15(postgres)

    rows = before_v15.execute("SELECT code, feed_time_zone FROM sources WHERE feed_time_zone IS NOT NULL").fetchall()
    assert rows == [("CNNTURK", "Europe/Istanbul")]


def test_nothing_changes_if_an_article_would_move_to_another_month(
    postgres: PostgresContainer, before_v15: psycopg.Connection
) -> None:
    """1 Aralık 01:00 olarak kaydedilen haber gerçekte 30 Kasım 22:00 UTC'dir: aylık indeksi değişirdi.

    Belgenin başka bir indekse taşınması bu betiğin işi değildir; betik hiçbir şey değiştirmeden durur.
    """
    moving = insert_article(before_v15, "CNNTURK", datetime(2026, 12, 1, 1, 0, tzinfo=UTC))

    with pytest.raises(psycopg.errors.RaiseException, match="başka bir aya"):
        apply_v15(postgres)

    assert published_at_of(before_v15, moving) == datetime(2026, 12, 1, 1, 0, tzinfo=UTC)
    columns = before_v15.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_name = 'sources' AND column_name = 'feed_time_zone'"
    ).fetchall()
    assert columns == []
