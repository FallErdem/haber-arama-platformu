"""V14 geçiş betiği: metin sütunları silinmeden önce, Elasticsearch'te karşılığı olmayan metinler outbox
notlarına taşınır (ADR-0019).

Betik kümede bir kez, işçi durdurulmuşken çalışır. O an aktarılmamış bir haber (işçinin son turunda
kaydedilip notu henüz işlenmemiş) veya belgesi eski düzende indeksten silinmiş gizli bir haber varsa,
metni kaybolmamalı ve yeni işçi onu nottan alabilmelidir.
"""

from collections.abc import Iterator
from typing import Any
from uuid import UUID

import psycopg
import pytest
from conftest import admin_connect, apply_migrations
from testcontainers.community.postgres import PostgresContainer

from news_worker.search_document import ArticleTexts

DATABASE = "migration_v14"


@pytest.fixture
def before_v14(postgres: PostgresContainer) -> Iterator[psycopg.Connection]:
    """V13'e kadar kurulmuş ayrı bir veritabanına süper kullanıcı bağlantısı; test bitince silinir."""
    with admin_connect(postgres) as admin:
        admin.execute(f"CREATE DATABASE {DATABASE} OWNER news_owner")
    try:
        apply_migrations(postgres, DATABASE, to_version=13)
        with admin_connect(postgres, DATABASE) as connection:
            yield connection
    finally:
        with admin_connect(postgres) as admin:
            admin.execute(f"DROP DATABASE {DATABASE} WITH (FORCE)")


def insert_old_article(connection: psycopg.Connection, key: str, *, hidden: bool = False) -> UUID:
    """V14'ten önceki biçimde bir haber: metinleri haber tablosunda."""
    row = connection.execute(
        """
        INSERT INTO articles (source_id, external_id, url, normalized_url, title, summary, content, author,
                              language, item_type, published_at, fetched_at, lifecycle_state)
        SELECT id, %(key)s, %(url)s, %(url)s, %(key)s, %(key)s || ' özeti', '<p>' || %(key)s || ' metni</p>',
               %(key)s || ' yazarı', 'tr', 'ARTICLE', now(), now(), 'HOT'
        FROM sources WHERE code = 'TRT'
        RETURNING id
        """,
        {"key": key, "url": f"https://example.test/{key}"},
    ).fetchone()
    assert row is not None
    article_id: UUID = row[0]
    if hidden:
        connection.execute(
            """
            WITH admin AS (
                INSERT INTO users (keycloak_sub, email, role, status)
                VALUES (%(key)s, %(key)s || '@example.test', 'ADMIN', 'ACTIVE')
                RETURNING id
            )
            UPDATE articles SET hidden = true, hidden_at = now(), hidden_by = (SELECT id FROM admin)
            WHERE id = %(id)s
            """,
            {"key": key, "id": article_id},
        )
    return article_id


def insert_note(connection: psycopg.Connection, article_id: UUID, operation: str, status: str) -> UUID:
    row = connection.execute(
        """
        INSERT INTO outbox_events (article_id, operation, status, next_attempt_at, processed_at)
        VALUES (%s, %s, %s, now(), CASE WHEN %s = 'PROCESSED' THEN now() END)
        RETURNING id
        """,
        (article_id, operation, status, status),
    ).fetchone()
    assert row is not None
    note_id: UUID = row[0]
    return note_id


def notes_of(connection: psycopg.Connection, article_id: UUID) -> list[tuple[str, str, Any]]:
    """Haberin notları (tür, durum, metin), oluşturulma sırasıyla."""
    return connection.execute(
        "SELECT operation, status, payload FROM outbox_events WHERE article_id = %s ORDER BY id",
        (article_id,),
    ).fetchall()


def apply_v14(postgres: PostgresContainer) -> None:
    apply_migrations(postgres, DATABASE, from_version=14, to_version=14)


def test_pending_note_receives_the_texts_before_the_columns_are_dropped(
    postgres: PostgresContainer, before_v14: psycopg.Connection
) -> None:
    article_id = insert_old_article(before_v14, "bekleyen")
    insert_note(before_v14, article_id, "INDEX", "PENDING")

    apply_v14(postgres)

    [(operation, status, payload)] = notes_of(before_v14, article_id)
    assert (operation, status) == ("INDEX", "PENDING")
    # Yeni işçi metni nottan bu biçimde okur.
    assert ArticleTexts.from_payload(payload) == ArticleTexts(
        summary="bekleyen özeti", content="<p>bekleyen metni</p>", author="bekleyen yazarı"
    )


def test_processed_note_stays_without_texts(postgres: PostgresContainer, before_v14: psycopg.Connection) -> None:
    # Metni zaten Elasticsearch'te; PostgreSQL'de kopyası kalmamalı.
    article_id = insert_old_article(before_v14, "aktarilmis")
    insert_note(before_v14, article_id, "INDEX", "PROCESSED")

    apply_v14(postgres)

    assert notes_of(before_v14, article_id) == [("INDEX", "PROCESSED", None)]


def test_hidden_article_gets_a_note_with_its_texts(postgres: PostgresContainer, before_v14: psycopg.Connection) -> None:
    # Eski düzende gizlenen haberin belgesi indeksten silinmişti; metni yalnızca haber tablosundaydı.
    article_id = insert_old_article(before_v14, "gizli", hidden=True)
    insert_note(before_v14, article_id, "DELETE", "PROCESSED")

    apply_v14(postgres)

    old_note, new_note = notes_of(before_v14, article_id)
    assert old_note == ("DELETE", "PROCESSED", None)
    assert new_note[:2] == ("INDEX", "PENDING")
    assert ArticleTexts.from_payload(new_note[2]) == ArticleTexts(
        summary="gizli özeti", content="<p>gizli metni</p>", author="gizli yazarı"
    )


def test_text_columns_are_dropped(postgres: PostgresContainer, before_v14: psycopg.Connection) -> None:
    apply_v14(postgres)

    columns = before_v14.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'articles'"
    ).fetchall()
    assert {"summary", "content", "author"}.isdisjoint(name for (name,) in columns)
