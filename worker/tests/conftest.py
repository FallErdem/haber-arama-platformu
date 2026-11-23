"""Testlerin ortak hazırlığı: geçici bir PostgreSQL konteyneri ve üzerinde gerçek şema.

Konteyner bütün test oturumu için bir kez açılır. Kümede CloudNativePG'nin ve
Flyway'in yaptığı işler burada elle yapılır: roller oluşturulur ve
db/migrations/ altındaki betikler sırayla uygulanır. Böylece testler, işçinin
gerçekte göreceği tablolar ve yetkilerle çalışır.
"""

import io
import json
import re
import time
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

import httpx
import psycopg
import pytest
from elasticsearch import AsyncElasticsearch
from PIL import Image
from prometheus_client.parser import text_string_to_metric_families
from testcontainers.community.postgres import PostgresContainer
from testcontainers.core.container import DockerContainer

from news_worker.config import Settings
from news_worker.database import Database
from news_worker.metrics import WorkerMetrics
from news_worker.object_storage import ObjectStorage, create_storage_client
from news_worker.search_index import INDEX_PATTERN, create_search_client

if TYPE_CHECKING:
    from types_boto3_s3 import S3Client

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
    CREATE ROLE news_backup LOGIN PASSWORD 'test-backup' IN ROLE pg_read_all_data;
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
    DELETE FROM feed_tests;
    DELETE FROM users;
    DELETE FROM ingestion_runs;
    UPDATE sources SET enabled = true, purge_requested_at = NULL;
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


def metric_value(metrics: WorkerMetrics, name: str, **labels: str) -> float | None:
    """Bir ölçümün, Prometheus'un okuduğu çıktıdaki değeri; çıktıda yoksa None.

    Çıktı, Prometheus kütüphanesinin kendi ayrıştırıcısıyla okunur; test Prometheus'un gördüğünü denetler.
    """
    for family in text_string_to_metric_families(metrics.render().decode()):
        for sample in family.samples:
            if sample.name == name and sample.labels == labels:
                return sample.value
    return None


def _migration_version(path: Path) -> int:
    match = re.match(r"V(\d+)__", path.name)
    assert match is not None, f"Beklenmeyen betik adı: {path.name}"
    return int(match.group(1))


def apply_migrations(
    postgres: PostgresContainer,
    dbname: str = "news",
    from_version: int = 1,
    to_version: int | None = None,
) -> None:
    """Geçiş betiklerini uygular; sürüm aralığı verilirse yalnızca o aralıktakileri.

    Flyway'in yaptığı gibi: betikler sürüm numarasına göre sıralanır ve tabloların sahibi olan
    news_owner ile, her biri kendi işleminde çalıştırılır.
    """
    with psycopg.connect(
        host=postgres.get_container_host_ip(),
        port=int(postgres.get_exposed_port(5432)),
        dbname=dbname,
        user="news_owner",
        password="test-owner",
    ) as connection:
        for path in sorted(MIGRATIONS_DIR.glob("V*.sql"), key=_migration_version):
            version = _migration_version(path)
            if version < from_version or (to_version is not None and version > to_version):
                continue
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
        apply_migrations(container)
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
        # Kimsenin dinlemediği bir adres: Elasticsearch gerektiren testler gerçek adresi kendileri verir.
        es_url="http://127.0.0.1:9",
        es_user=SEARCH_WORKER_USER,
        es_password=SEARCH_WORKER_PASSWORD,
        # Kimsenin dinlemediği bir adres: MinIO gerektiren testler gerçek adresi kendileri verir.
        minio_url="http://127.0.0.1:9",
        minio_access_key=STORAGE_WORKER_USER,
        minio_secret_key=STORAGE_WORKER_PASSWORD,
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


@pytest.fixture
def trt_feed(admin: psycopg.Connection) -> tuple[UUID, UUID]:
    """TRT kaynağının ve bir beslemesinin kimlikleri. `admin` kullanıldığı için test sonunda haberler silinir."""
    row = admin.execute(
        "SELECT s.id, f.id FROM feeds f JOIN sources s ON s.id = f.source_id "
        "WHERE s.code = 'TRT' ORDER BY f.name LIMIT 1"
    ).fetchone()
    assert row is not None
    return row[0], row[1]


# --- Elasticsearch -------------------------------------------------------------------------

# Kümedeki Elasticsearch ile aynı sürüm ve aynı güvenlik ayarları (deploy/k8s/base/elasticsearch).
ELASTICSEARCH_IMAGE = "docker.elastic.co/elasticsearch/elasticsearch:9.4.9"
ELASTIC_PASSWORD = "test-elastic"
SEARCH_WORKER_USER = "news_worker"
SEARCH_WORKER_PASSWORD = "test-search-worker"

# İşçinin Elasticsearch rolü. Kümede bu rolü elasticsearch-setup Job'u oluşturur
# (deploy/k8s/base/elasticsearch/setup-job.yaml); burada aynısı elle oluşturulur. Böylece testler
# süper kullanıcıyla değil, işçinin gerçekte sahip olduğu yetkilerle çalışır.
SEARCH_WORKER_ROLE = {
    "cluster": ["monitor", "manage_ilm", "manage_index_templates"],
    "indices": [
        {
            "names": ["articles-*", "articles"],
            "privileges": ["create_index", "write", "read", "manage", "view_index_metadata"],
        }
    ],
}


def _wait_until_elasticsearch_is_up(url: str, timeout_seconds: float = 180) -> None:
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            response = httpx.get(
                f"{url}/_cluster/health",
                params={"wait_for_status": "yellow", "timeout": "5s"},
                auth=("elastic", ELASTIC_PASSWORD),
                timeout=10,
            )
            if response.status_code == httpx.codes.OK:
                return
        except httpx.HTTPError:
            pass
        if time.monotonic() > deadline:
            raise TimeoutError("Elasticsearch konteyneri zamanında hazır olmadı")
        time.sleep(1)


@pytest.fixture(scope="session")
def elasticsearch_url() -> Iterator[str]:
    """Bütün test oturumu için bir kez açılan geçici Elasticsearch; oturum bitince silinir."""
    container = (
        DockerContainer(ELASTICSEARCH_IMAGE)
        .with_exposed_ports(9200)
        .with_env("discovery.type", "single-node")
        .with_env("xpack.security.enabled", "true")
        .with_env("xpack.security.http.ssl.enabled", "false")
        .with_env("xpack.security.transport.ssl.enabled", "false")
        .with_env("ELASTIC_PASSWORD", ELASTIC_PASSWORD)
        .with_env("ES_JAVA_OPTS", "-Xms512m -Xmx512m")
    )
    with container:
        url = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(9200)}"
        _wait_until_elasticsearch_is_up(url)
        admin_auth = ("elastic", ELASTIC_PASSWORD)
        httpx.put(f"{url}/_security/role/news_worker", json=SEARCH_WORKER_ROLE, auth=admin_auth).raise_for_status()
        httpx.put(
            f"{url}/_security/user/{SEARCH_WORKER_USER}",
            json={"password": SEARCH_WORKER_PASSWORD, "roles": ["news_worker"]},
            auth=admin_auth,
        ).raise_for_status()
        yield url


@pytest.fixture
async def search_client(elasticsearch_url: str) -> AsyncIterator[AsyncElasticsearch]:
    """İşçinin kendi kullanıcısıyla bağlanan istemci. Test bitince testin açtığı indeksler ve şablonlar silinir."""
    client = create_search_client(
        elasticsearch_url, SEARCH_WORKER_USER, SEARCH_WORKER_PASSWORD, request_timeout_seconds=30
    )
    try:
        yield client
    finally:
        # Elasticsearch joker karakterle silmeye izin vermez; indeksler adlarıyla silinir.
        # expand_wildcards: bir testin kapattığı indeks de bulunup silinir.
        indices = await client.indices.get(index=INDEX_PATTERN, expand_wildcards="all")
        if indices.body:
            await client.indices.delete(index=",".join(indices.body))
        # Şablonlar da silinir: bir testin etkin yaptığı nesil sonraki testi etkilemez.
        templates = await client.options(ignore_status=404).indices.get_index_template(name="articles*")
        for template in templates.get("index_templates", []):
            await client.indices.delete_index_template(name=template["name"])
        await client.close()


def make_image(image_format: str = "JPEG", size: tuple[int, int] = (40, 30)) -> bytes:
    """Testlerde kullanılan küçük bir görsel: verilen türde ve boyutlarda, tek renkli."""
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(200, 30, 30)).save(buffer, format=image_format)
    return buffer.getvalue()


# --- MinIO -------------------------------------------------------------------------------------

# Kümedeki MinIO ile aynı sürüm (deploy/k8s/base/minio). Kümede sunucu "-distroless" imajla çalışır;
# testte kurulum adımları için kabuk ve mc istemcisi gerektiğinden aynı sürümün standart imajı kullanılır.
MINIO_IMAGE = "docker.io/pgsty/silo:RELEASE.2026-10-26T00-00-00Z"
MINIO_ROOT_USER = "test-root"
MINIO_ROOT_PASSWORD = "test-root-password"
STORAGE_WORKER_USER = "news-worker"
STORAGE_WORKER_PASSWORD = "test-storage-worker"
MEDIA_BUCKET = "media"

# İşçinin MinIO politikası. Kümede bunu minio-setup Job'u oluşturur
# (deploy/k8s/base/minio/setup-job.yaml); burada aynısı elle oluşturulur.
STORAGE_WORKER_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
            "Resource": ["arn:aws:s3:::media/*"],
        },
        {"Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": ["arn:aws:s3:::media"]},
    ],
}


def _wait_until_minio_is_up(url: str, timeout_seconds: float = 120) -> None:
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            if httpx.get(f"{url}/minio/health/live", timeout=5).status_code == httpx.codes.OK:
                return
        except httpx.HTTPError:
            pass
        if time.monotonic() > deadline:
            raise TimeoutError("MinIO konteyneri zamanında hazır olmadı")
        time.sleep(1)


@pytest.fixture(scope="session")
def minio_url() -> Iterator[str]:
    """Bütün test oturumu için bir kez açılan geçici MinIO: kova, işçinin politikası ve kullanıcısı hazır."""
    container = (
        DockerContainer(MINIO_IMAGE)
        .with_command("server /data")
        .with_exposed_ports(9000)
        .with_env("MINIO_ROOT_USER", MINIO_ROOT_USER)
        .with_env("MINIO_ROOT_PASSWORD", MINIO_ROOT_PASSWORD)
    )
    with container:
        url = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(9000)}"
        _wait_until_minio_is_up(url)
        # Kurulum, kümedeki Job gibi mc ile ve konteynerin içinden yapılır.
        policy = json.dumps(STORAGE_WORKER_POLICY)
        script = f"""
            set -e
            mc alias set local http://127.0.0.1:9000 {MINIO_ROOT_USER} {MINIO_ROOT_PASSWORD}
            mc mb --ignore-existing local/{MEDIA_BUCKET}
            echo '{policy}' > /tmp/news-worker.json
            mc admin policy create local news-worker /tmp/news-worker.json
            mc admin user add local {STORAGE_WORKER_USER} {STORAGE_WORKER_PASSWORD}
            mc admin policy attach local news-worker --user {STORAGE_WORKER_USER}
        """
        result = container.exec(["sh", "-c", script])
        assert result.exit_code == 0, result.output.decode()
        yield url


@pytest.fixture
def storage_client(minio_url: str) -> Iterator[S3Client]:
    """İşçinin kendi kullanıcısıyla bağlanan S3 istemcisi. Test bitince testin yüklediği dosyalar silinir."""
    client = create_storage_client(minio_url, STORAGE_WORKER_USER, STORAGE_WORKER_PASSWORD, timeout_seconds=10)
    try:
        yield client
    finally:
        listed = client.list_objects_v2(Bucket=MEDIA_BUCKET, Prefix="articles/")
        for item in listed.get("Contents", []):
            client.delete_object(Bucket=MEDIA_BUCKET, Key=item["Key"])


@pytest.fixture
def storage(storage_client: S3Client) -> ObjectStorage:
    return ObjectStorage(storage_client, MEDIA_BUCKET)
