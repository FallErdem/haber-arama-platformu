"""Bir performans testi aralığının sunucu tarafı ölçümlerini Prometheus'tan özetler (İ-38).

Kullanım: python3 tests/performance/prometheus_summary.py <başlangıç> <bitiş>   (UTC, ör. 2026-11-24T18:10:40Z)

Prometheus'a kubectl'in API sunucusu üzerinden ulaşılır (port-forward gerekmez). Çıktı: bileşenlerin CPU ve bellek
kullanımı, API'nin JVM heap'i ve bağlantı havuzu, uç nokta bazında sunucu tarafı yanıt süreleri ve 5xx sayısı.
"""

import json
import subprocess
import sys
import urllib.parse
from datetime import datetime

BASE = "/api/v1/namespaces/monitoring/services/prometheus-server:80/proxy/api/v1"
PODS = "api-.*|elasticsearch-0|postgres-1|keycloak-.*|minio-0|worker-.*"
ENDPOINTS = ("/api/v1/articles", "/api/v1/articles/{id}", "/api/v1/media/{id}", "/api/v1/me/saved-articles")


def query(path: str, **params: object) -> list[dict]:
    url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
    output = subprocess.run(["kubectl", "get", "--raw", url], capture_output=True, text=True, check=True).stdout
    result: list[dict] = json.loads(output)["data"]["result"]
    return result


def timestamp(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def print_series(promql: str, start: float, end: float, label: str = "pod") -> None:
    """Aralıktaki değerlerin ortalaması, en büyüğü, ilki ve sonu (30 saniyelik adımlarla)."""
    for result in query("query_range", query=promql, start=start, end=end, step=30):
        values = [float(v[1]) for v in result["values"] if v[1] not in ("NaN", "+Inf")]
        if values:
            name = result["metric"].get(label, "-")
            print(
                f"   {name:32} ort {sum(values) / len(values):10.3f}  en çok {max(values):10.3f}"
                f"  ilk {values[0]:10.3f}  son {values[-1]:10.3f}"
            )


def main() -> None:
    start, end = timestamp(sys.argv[1]), timestamp(sys.argv[2])
    window = int(end - start)
    print(f"Aralık: {sys.argv[1]} – {sys.argv[2]} ({window // 60} dk)")
    print("CPU (çekirdek):")
    # cAdvisor bu kümede CPU'yu pod düzeyinde verir (container etiketi yok); bellek kapsayıcı düzeyindedir.
    print_series(f'sum by (pod) (rate(container_cpu_usage_seconds_total{{namespace="haber",pod=~"{PODS}"}}[1m]))', start, end)
    print("Bellek (MB, working set):")
    print_series(
        f'sum by (pod) (container_memory_working_set_bytes{{namespace="haber",container!="",pod=~"{PODS}"}}) / 1048576',
        start,
        end,
    )
    print("API JVM heap (MB):")
    print_series('sum by (pod) (jvm_memory_used_bytes{area="heap"}) / 1048576', start, end)
    print("API bağlantı havuzu (Hikari): etkin, bekleyen")
    print_series("sum(hikaricp_connections_active)", start, end, label="-")
    print_series("sum(hikaricp_connections_pending)", start, end, label="-")
    print("API sunucu tarafı süreler (ms), bütün aralık:")
    for uri in ENDPOINTS:
        parts = []
        for quantile in (0.5, 0.95, 0.99):
            promql = (
                f"histogram_quantile({quantile}, sum by (le) "
                f'(increase(http_server_requests_seconds_bucket{{uri="{uri}"}}[{window}s])))'
            )
            result = query("query", query=promql, time=end)
            value = float(result[0]["value"][1]) * 1000 if result and result[0]["value"][1] != "NaN" else float("nan")
            parts.append(f"p{int(quantile * 100)} {value:7.1f}")
        count = query("query", query=f'sum(increase(http_server_requests_seconds_count{{uri="{uri}"}}[{window}s]))', time=end)
        total = float(count[0]["value"][1]) if count else 0.0
        print(f"   {uri:32} {'  '.join(parts)}  istek {total:9.0f}")
    errors = query("query", query=f'sum(increase(http_server_requests_seconds_count{{status=~"5.."}}[{window}s]))', time=end)
    print("API 5xx yanıt:", round(float(errors[0]["value"][1])) if errors else 0)


if __name__ == "__main__":
    main()
