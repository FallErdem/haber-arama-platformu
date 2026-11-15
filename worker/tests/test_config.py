import pytest

from news_worker.config import ConfigurationError, Settings


def test_defaults_are_used_when_only_password_is_given() -> None:
    """Yalnızca şifre verildiğinde varsayılan değerler kullanılır."""
    settings = Settings.from_environment({"DB_PASSWORD": "gizli"})

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


def test_environment_variables_override_defaults() -> None:
    """Ortam değişkenleri varsayılan değerlerin yerine geçer."""
    settings = Settings.from_environment(
        {
            "DB_PASSWORD": "gizli",
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


@pytest.mark.parametrize("environment", [{}, {"DB_PASSWORD": ""}])
def test_missing_password_raises_a_clear_error(environment: dict[str, str]) -> None:
    """Şifre yoksa hangi ayarın eksik olduğunu söyleyen bir hata verir."""
    with pytest.raises(ConfigurationError, match="DB_PASSWORD"):
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
    ],
)
def test_invalid_numeric_setting_is_rejected(name: str, value: str) -> None:
    """Sayı olmayan veya sıfırdan büyük olmayan sayısal ayar reddedilir."""
    with pytest.raises(ConfigurationError, match=name):
        Settings.from_environment({"DB_PASSWORD": "gizli", name: value})


def test_password_is_hidden_in_repr() -> None:
    """Şifre, ayarların yazdırılan halinde görünmez."""
    settings = Settings.from_environment({"DB_PASSWORD": "cok-gizli-sifre"})

    assert "cok-gizli-sifre" not in repr(settings)
