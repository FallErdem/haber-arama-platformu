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
    scheduler_interval_seconds: float
    health_port: int

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if environment is None else environment

        password = env.get("DB_PASSWORD", "")
        if not password:
            raise ConfigurationError("DB_PASSWORD ortam değişkeni tanımlı değil")

        return cls(
            db_host=env.get("DB_HOST", "localhost"),
            db_port=_positive_int(env, "DB_PORT", 5432),
            db_name=env.get("DB_NAME", "news"),
            # İşçi yalnızca kendi kullanıcısıyla bağlanır; yetkileri V9 betiğinde tanımlıdır.
            db_user=env.get("DB_USER", "news_worker"),
            db_password=password,
            scheduler_interval_seconds=_positive_float(env, "SCHEDULER_INTERVAL_SECONDS", 30.0),
            health_port=_positive_int(env, "HEALTH_PORT", 8080),
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
