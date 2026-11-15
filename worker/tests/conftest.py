"""Testlerin ortak hazırlığı: geçici bir PostgreSQL konteyneri ve üzerinde gerçek şema.

Konteyner bütün test oturumu için bir kez açılır. Kümede CloudNativePG'nin ve
Flyway'in yaptığı işler burada elle yapılır: roller oluşturulur ve
db/migrations/ altındaki betikler sırayla uygulanır. Böylece testler, işçinin
gerçekte göreceği tablolar ve yetkilerle çalışır.
"""

import re
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from news_worker.config import Settings
from news_worker.database import Database

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"

# Kümedeki PostgreSQL ile aynı sürüm ve aynı Debian tabanı (ADR-0018).
POSTGRES_IMAGE = "postgres:18.4-trixie"
ADMIN_USER = "test"
ADMIN_PASSWORD = "test"
WORKER_PASSWORD = "test-worker"

# Şifreler yalnızca test bitince silinen bu konteynere aittir.
CREATE_ROLES_SQL = """
    CREATE ROLE news_owner LOGIN PASSWORD 'test-owner';
    CREATE ROLE news_app LOGIN PASSWORD 'test-app';
    CREATE ROLE news_worker LOGIN PASSWORD 'test-worker';
    ALTER DATABASE news OWNER TO news_owner;
"""

# Şeması olmayan ikinci bir veritabanı: "tablolar henüz hazır değil" durumunu sınamak için.
# CREATE DATABASE başka komutlarla aynı istekte çalıştırılamaz; bu yüzden ayrıdır.
CREATE_EMPTY_DATABASE_SQL = "CREATE DATABASE empty"

# Testlerin değiştirebildiği her şey başlangıç durumuna döner. Haber silinince kategorileri
# ve görselleri de silinir (ON DELETE CASCADE); outbox kayıtları habere bağlı olmadığı için ayrıca silinir.
RESET_DATA_SQL = """
    DELETE FROM outbox_events;
    DELETE FROM articles;
    DELETE FROM ingestion_runs;
    UPDATE sources SET enabled = true;
    UPDATE feeds
    SET enabled = true, disabled_reason = NULL, next_fetch_at = now(), etag = NULL, last_modified = NULL,
        consecutive_failures = 0, last_success_at = NULL, last_error = NULL;
"""


def admin_connect(postgres: PostgresContainer, dbname: str = "news") -> psycopg.Connection:
    """Konteynerin süper kullanıcısıyla bağlanır; yalnızca test verisi hazırlamak içindir."""
    return psycopg.connect(
        host=postgres.get_container_host_ip(),
        port=int(postgres.get_exposed_port(5432)),
        dbname=dbname,
        user=ADMIN_USER,
        password=ADMIN_PASSWORD,
        autocommit=True,
    )


def count_enabled_feeds(admin: psycopg.Connection) -> int:
    """Etkin bir kaynağa ait etkin beslemelerin sayısı.

    Testler beklenen sayıyı sabit yazmak yerine buradan alır; yeni bir geçiş betiği
    besleme eklediğinde testlerin elle güncellenmesi gerekmez.
    """
    row = admin.execute(
        "SELECT count(*) FROM feeds f JOIN sources s ON s.id = f.source_id WHERE f.enabled AND s.enabled"
    ).fetchone()
    assert row is not None
    count: int = row[0]
    return count


def _migration_version(path: Path) -> int:
    match = re.match(r"V(\d+)__", path.name)
    assert match is not None, f"Beklenmeyen betik adı: {path.name}"
    return int(match.group(1))


def _apply_migrations(postgres: PostgresContainer) -> None:
    # Flyway'in yaptığı gibi: betikler sürüm numarasına göre sıralanır ve tabloların sahibi
    # olan news_owner ile, her biri kendi işleminde çalıştırılır.
    with psycopg.connect(
        host=postgres.get_container_host_ip(),
        port=int(postgres.get_exposed_port(5432)),
        dbname="news",
        user="news_owner",
        password="test-owner",
    ) as connection:
        for path in sorted(MIGRATIONS_DIR.glob("V*.sql"), key=_migration_version):
            connection.execute(path.read_bytes())
            connection.commit()


@pytest.fixture(scope="session")
def postgres() -> Iterator[PostgresContainer]:
    container = PostgresContainer(
        POSTGRES_IMAGE, username=ADMIN_USER, password=ADMIN_PASSWORD, dbname="news", driver=None
    ).with_env("POSTGRES_INITDB_ARGS", "--encoding=UTF8 --locale=C")
    with container:
        with admin_connect(container) as connection:
            connection.execute(CREATE_ROLES_SQL)
            connection.execute(CREATE_EMPTY_DATABASE_SQL)
        _apply_migrations(container)
        yield container


@pytest.fixture
def settings(postgres: PostgresContainer) -> Settings:
    """İşçinin gerçekte kullandığı kullanıcıyla (news_worker) bağlanan ayarlar."""
    return Settings(
        db_host=postgres.get_container_host_ip(),
        db_port=int(postgres.get_exposed_port(5432)),
        db_name="news",
        db_user="news_worker",
        db_password=WORKER_PASSWORD,
        scheduler_interval_seconds=0.05,
        health_port=8080,
    )


@pytest.fixture
def database(settings: Settings) -> Database:
    return Database(settings)


@pytest.fixture
def admin(postgres: PostgresContainer) -> Iterator[psycopg.Connection]:
    """Test verisini değiştirmek için süper kullanıcı bağlantısı.

    Test bitince veriler başlangıç durumuna döndürülür; testler birbirini etkilemez.
    """
    with admin_connect(postgres) as connection:
        yield connection
        connection.execute(RESET_DATA_SQL)
