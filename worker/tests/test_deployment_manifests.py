"""İşçinin Kubernetes tanımlarının, işçinin zorunlu ayarlarını verdiğinin denetimi.

İşçinin imajı iki yerde çalışır: sürekli çalışan işçi (Deployment) ve elle başlatılan tam yeniden
indeksleme (CronJob). İkisi de aynı ayar sınıfını okur; zorunlu bir ayar birine verilip diğerine
verilmezse komut kümede açılışta durur. 18 Kasım 2026'da MinIO şifresi (İ-14'te zorunlu oldu)
yeniden indeksleme tanımına eklenmediği için yeniden indeksleme başlayamadı.
"""

import re
from pathlib import Path

import pytest

from news_worker.config import ConfigurationError, Settings

WORKER_MANIFESTS = Path(__file__).resolve().parents[2] / "deploy/k8s/base/worker"

_MISSING_SETTING = re.compile(r"^([A-Z_]+) ortam değişkeni tanımlı değil$")


def required_settings() -> list[str]:
    """Ayar sınıfının zorunlu tuttuğu ortam değişkenleri, koddan çıkarılır.

    Boş bir ortamla başlanır; her seferinde eksik olduğu bildirilen değişkene örnek bir değer verilir.
    Böylece işçiye yeni bir zorunlu ayar eklendiğinde bu liste kendiliğinden güncellenir.
    """
    environment: dict[str, str] = {}
    while True:
        try:
            Settings.from_environment(environment)
        except ConfigurationError as error:
            match = _MISSING_SETTING.match(str(error))
            assert match is not None, f"Beklenmeyen ayar hatası: {error}"
            environment[match.group(1)] = "ornek"
            continue
        return sorted(environment)


def test_required_settings_are_found_from_the_code() -> None:
    """Zorunlu ayarlar koddan bulunur: veritabanı, Elasticsearch ve MinIO şifreleri."""
    assert required_settings() == ["DB_PASSWORD", "ES_PASSWORD", "MINIO_SECRET_KEY"]


@pytest.mark.parametrize("manifest", ["deployment.yaml", "reindex-cronjob.yaml"])
def test_every_required_setting_is_given_to_the_worker_image(manifest: str) -> None:
    """İşçinin imajını çalıştıran her Kubernetes tanımı, işçinin bütün zorunlu ayarlarını verir."""
    content = (WORKER_MANIFESTS / manifest).read_text(encoding="utf-8")

    missing = [name for name in required_settings() if f"- name: {name}\n" not in content]

    assert missing == [], f"{manifest} şu zorunlu ayarları vermiyor: {missing}"
