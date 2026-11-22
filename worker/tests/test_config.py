import pytest

from news_worker.config import ConfigurationError, Settings


def test_defaults_are_used_when_only_password_is_given() -> None:
    """Yalnızca şifre verildiğinde varsayılan değerler kullanılır."""
    settings = Settings.from_environment(
        {"DB_PASSWORD": "gizli", "ES_PASSWORD": "arama-gizli", "MINIO_SECRET_KEY": "depo-gizli"}
    )

    assert settings.db_host == "localhost"
    assert settings.db_port == 5432
    assert settings.db_name == "news"
    assert settings.db_user == "news_worker"
    assert settings.db_password == "gizli"
    assert settings.scheduler_interval_seconds == 30.0
    assert settings.health_port == 8080
    assert settings.http_user_agent == "HaberAramaPlatformu/0.1 (egitim projesi)"
    assert settings.http_timeout_seconds == 10.0
    assert settings.http_total_timeout_seconds == 30.0
    assert settings.es_url == "http://localhost:9200"
    assert settings.es_user == "news_worker"
    assert settings.es_password == "arama-gizli"
    assert settings.es_timeout_seconds == 30.0
    assert settings.outbox_interval_seconds == 5.0
    assert settings.outbox_batch_size == 200
    assert settings.minio_url == "http://localhost:9000"
    assert settings.minio_access_key == "news-worker"
    assert settings.minio_secret_key == "depo-gizli"
    assert settings.media_bucket == "media"
    assert settings.media_interval_seconds == 10.0
    assert settings.media_batch_size == 100
    assert settings.purge_interval_seconds == 60.0
    assert settings.purge_batch_size == 500
    assert settings.maintenance_interval_seconds == 43200.0
    assert settings.outbox_retention_days == 7
    assert settings.ingestion_run_retention_days == 180
    assert settings.feed_test_retention_days == 1


def test_environment_variables_override_defaults() -> None:
    """Ortam değişkenleri varsayılan değerlerin yerine geçer."""
    settings = Settings.from_environment(
        {
            "DB_PASSWORD": "gizli",
            "ES_PASSWORD": "arama-gizli",
            "MINIO_SECRET_KEY": "depo-gizli",
            "ES_URL": "http://elasticsearch:9200",
            "ES_USER": "baska_kullanici",
            "ES_TIMEOUT_SECONDS": "7",
            "OUTBOX_INTERVAL_SECONDS": "1.5",
            "OUTBOX_BATCH_SIZE": "50",
            "MINIO_URL": "http://minio:9000",
            "MINIO_ACCESS_KEY": "baska-kullanici",
            "MEDIA_BUCKET": "gorseller",
            "MEDIA_INTERVAL_SECONDS": "3",
            "MEDIA_BATCH_SIZE": "20",
            "PURGE_INTERVAL_SECONDS": "15",
            "PURGE_BATCH_SIZE": "50",
            "MAINTENANCE_INTERVAL_SECONDS": "600",
            "OUTBOX_RETENTION_DAYS": "3",
            "INGESTION_RUN_RETENTION_DAYS": "90",
            "FEED_TEST_RETENTION_DAYS": "2",
            "DB_HOST": "postgres-rw",
            "DB_PORT": "6432",
            "DB_NAME": "haberler",
            "SCHEDULER_INTERVAL_SECONDS": "2.5",
            "HEALTH_PORT": "9090",
            "HTTP_USER_AGENT": "BaskaAd/1.0",
            "HTTP_TIMEOUT_SECONDS": "3",
            "HTTP_TOTAL_TIMEOUT_SECONDS": "12.5",
        }
    )

    assert settings.db_host == "postgres-rw"
    assert settings.db_port == 6432
    assert settings.db_name == "haberler"
    assert settings.scheduler_interval_seconds == 2.5
    assert settings.health_port == 9090
    assert settings.http_user_agent == "BaskaAd/1.0"
    assert settings.http_timeout_seconds == 3.0
    assert settings.http_total_timeout_seconds == 12.5
    assert settings.es_url == "http://elasticsearch:9200"
    assert settings.es_user == "baska_kullanici"
    assert settings.es_timeout_seconds == 7.0
    assert settings.outbox_interval_seconds == 1.5
    assert settings.outbox_batch_size == 50
    assert settings.minio_url == "http://minio:9000"
    assert settings.minio_access_key == "baska-kullanici"
    assert settings.media_bucket == "gorseller"
    assert settings.media_interval_seconds == 3.0
    assert settings.media_batch_size == 20
    assert settings.purge_interval_seconds == 15.0
    assert settings.purge_batch_size == 50
    assert settings.maintenance_interval_seconds == 600.0
    assert settings.outbox_retention_days == 3
    assert settings.ingestion_run_retention_days == 90
    assert settings.feed_test_retention_days == 2


@pytest.mark.parametrize(
    ("environment", "missing"),
    [
        ({"ES_PASSWORD": "arama-gizli", "MINIO_SECRET_KEY": "depo-gizli"}, "DB_PASSWORD"),
        ({"DB_PASSWORD": "", "ES_PASSWORD": "arama-gizli", "MINIO_SECRET_KEY": "depo-gizli"}, "DB_PASSWORD"),
        ({"DB_PASSWORD": "gizli"}, "ES_PASSWORD"),
        ({"DB_PASSWORD": "gizli", "ES_PASSWORD": ""}, "ES_PASSWORD"),
        ({"DB_PASSWORD": "gizli", "ES_PASSWORD": "arama-gizli"}, "MINIO_SECRET_KEY"),
        ({"DB_PASSWORD": "gizli", "ES_PASSWORD": "arama-gizli", "MINIO_SECRET_KEY": ""}, "MINIO_SECRET_KEY"),
    ],
)
def test_missing_password_raises_a_clear_error(environment: dict[str, str], missing: str) -> None:
    """Bir şifre yoksa hangi ayarın eksik olduğunu söyleyen bir hata verir."""
    with pytest.raises(ConfigurationError, match=missing):
        Settings.from_environment(environment)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("DB_PORT", "abc"),
        ("DB_PORT", "0"),
        ("HEALTH_PORT", "-1"),
        ("SCHEDULER_INTERVAL_SECONDS", "hizli"),
        ("SCHEDULER_INTERVAL_SECONDS", "0"),
        ("HTTP_TIMEOUT_SECONDS", "uzun"),
        ("HTTP_TOTAL_TIMEOUT_SECONDS", "0"),
        ("ES_TIMEOUT_SECONDS", "0"),
        ("OUTBOX_INTERVAL_SECONDS", "sik"),
        ("OUTBOX_BATCH_SIZE", "0"),
        ("OUTBOX_BATCH_SIZE", "2.5"),
        ("MEDIA_INTERVAL_SECONDS", "0"),
        ("MEDIA_BATCH_SIZE", "yuz"),
        ("PURGE_INTERVAL_SECONDS", "0"),
        ("PURGE_BATCH_SIZE", "bes"),
        ("MAINTENANCE_INTERVAL_SECONDS", "0"),
        ("OUTBOX_RETENTION_DAYS", "0"),
        ("INGESTION_RUN_RETENTION_DAYS", "yarim"),
        ("FEED_TEST_RETENTION_DAYS", "1.5"),
    ],
)
def test_invalid_numeric_setting_is_rejected(name: str, value: str) -> None:
    """Sayı olmayan veya sıfırdan büyük olmayan sayısal ayar reddedilir."""
    with pytest.raises(ConfigurationError, match=name):
        Settings.from_environment(
            {"DB_PASSWORD": "gizli", "ES_PASSWORD": "arama-gizli", "MINIO_SECRET_KEY": "depo-gizli", name: value}
        )


def test_password_is_hidden_in_repr() -> None:
    """Şifreler, ayarların yazdırılan halinde görünmez."""
    settings = Settings.from_environment(
        {"DB_PASSWORD": "cok-gizli-sifre", "ES_PASSWORD": "arama-sifresi", "MINIO_SECRET_KEY": "depo-gizli"}
    )

    assert "cok-gizli-sifre" not in repr(settings)
    assert "arama-sifresi" not in repr(settings)
    assert "depo-gizli" not in repr(settings)
