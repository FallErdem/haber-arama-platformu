"""İşçinin ayarları. Hepsi ortam değişkenlerinden okunur; kodda şifre bulunmaz."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field


class ConfigurationError(Exception):
    """Bir ayar eksik veya geçersiz olduğunda fırlatılır."""


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    # repr=False: ayarlar loga yazılırsa veya bir hata mesajında görünürse şifre çıkmaz.
    db_password: str = field(repr=False)
    es_url: str
    es_user: str
    es_password: str = field(repr=False)
    minio_url: str
    minio_access_key: str
    minio_secret_key: str = field(repr=False)
    scheduler_interval_seconds: float
    health_port: int
    # Kaynak sitelere işçinin kendini tanıttığı ad (FG-VT-05).
    http_user_agent: str = "HaberAramaPlatformu/0.1 (egitim projesi)"
    # Bir isteğin her aşaması (bağlanma, yanıtı bekleme) için ayrı ayrı uygulanan süre.
    http_timeout_seconds: float = 10.0
    # Bir indirmenin baştan sona sürebileceği en uzun süre.
    http_total_timeout_seconds: float = 30.0
    # Elasticsearch'e giden bir isteğin süre sınırı.
    es_timeout_seconds: float = 30.0
    # Outbox aktarımının iki turu arasındaki süre ve bir turda işlenen en fazla not sayısı (ADR-0012).
    outbox_interval_seconds: float = 5.0
    outbox_batch_size: int = 200
    # Görsellerin yüklendiği kova (05-veri-modeli.md, 6. bölüm).
    media_bucket: str = "media"
    # Görsel indirme döngüsünün iki turu arasındaki süre ve bir turda alınan en fazla görsel sayısı.
    media_interval_seconds: float = 10.0
    media_batch_size: int = 100

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if environment is None else environment

        password = env.get("DB_PASSWORD", "")
        if not password:
            raise ConfigurationError("DB_PASSWORD ortam değişkeni tanımlı değil")
        es_password = env.get("ES_PASSWORD", "")
        if not es_password:
            raise ConfigurationError("ES_PASSWORD ortam değişkeni tanımlı değil")
        minio_secret_key = env.get("MINIO_SECRET_KEY", "")
        if not minio_secret_key:
            raise ConfigurationError("MINIO_SECRET_KEY ortam değişkeni tanımlı değil")

        return cls(
            db_host=env.get("DB_HOST", "localhost"),
            db_port=_positive_int(env, "DB_PORT", 5432),
            db_name=env.get("DB_NAME", "news"),
            # İşçi yalnızca kendi kullanıcısıyla bağlanır; yetkileri V9 betiğinde tanımlıdır.
            db_user=env.get("DB_USER", "news_worker"),
            db_password=password,
            es_url=env.get("ES_URL", "http://localhost:9200"),
            # Elasticsearch'te de yalnızca işçinin kendi kullanıcısı; rolü elasticsearch-setup Job'unda tanımlıdır.
            es_user=env.get("ES_USER", "news_worker"),
            es_password=es_password,
            minio_url=env.get("MINIO_URL", "http://localhost:9000"),
            # MinIO'da da yalnızca işçinin kendi kullanıcısı; yetkisi minio-setup Job'unda tanımlıdır.
            minio_access_key=env.get("MINIO_ACCESS_KEY", "news-worker"),
            minio_secret_key=minio_secret_key,
            scheduler_interval_seconds=_positive_float(env, "SCHEDULER_INTERVAL_SECONDS", 30.0),
            health_port=_positive_int(env, "HEALTH_PORT", 8080),
            http_user_agent=env.get("HTTP_USER_AGENT") or cls.http_user_agent,
            http_timeout_seconds=_positive_float(env, "HTTP_TIMEOUT_SECONDS", cls.http_timeout_seconds),
            http_total_timeout_seconds=_positive_float(
                env, "HTTP_TOTAL_TIMEOUT_SECONDS", cls.http_total_timeout_seconds
            ),
            es_timeout_seconds=_positive_float(env, "ES_TIMEOUT_SECONDS", cls.es_timeout_seconds),
            outbox_interval_seconds=_positive_float(env, "OUTBOX_INTERVAL_SECONDS", cls.outbox_interval_seconds),
            outbox_batch_size=_positive_int(env, "OUTBOX_BATCH_SIZE", cls.outbox_batch_size),
            media_bucket=env.get("MEDIA_BUCKET") or cls.media_bucket,
            media_interval_seconds=_positive_float(env, "MEDIA_INTERVAL_SECONDS", cls.media_interval_seconds),
            media_batch_size=_positive_int(env, "MEDIA_BATCH_SIZE", cls.media_batch_size),
        )


def _positive_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ConfigurationError(f"{name} bir tam sayı olmalı: {raw!r}") from None
    if value <= 0:
        raise ConfigurationError(f"{name} sıfırdan büyük olmalı: {raw!r}")
    return value


def _positive_float(env: Mapping[str, str], name: str, default: float) -> float:
    raw = env.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise ConfigurationError(f"{name} bir sayı olmalı: {raw!r}") from None
    if value <= 0:
        raise ConfigurationError(f"{name} sıfırdan büyük olmalı: {raw!r}")
    return value
