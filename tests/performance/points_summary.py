"""k6'nın istek zaman serisini (results/*-points.json.gz) dakika dakika özetler (İ-38).

Kullanım: python3 tests/performance/points_summary.py <points.json.gz>

Her dakika için: istek sayısı, hata oranı ve arama isteklerinin p95'i. Ani yük testinde yük düştükten sonraki
toparlanmayı, uzun süre testinde ilk ve son saat arasındaki farkı görmek için kullanılır.
"""

import gzip
import json
import sys
from collections import defaultdict
from datetime import datetime


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(fraction * len(ordered)))] if ordered else float("nan")


def main() -> None:
    requests: dict[str, int] = defaultdict(int)
    failures: dict[str, int] = defaultdict(int)
    search: dict[str, list[float]] = defaultdict(list)
    with gzip.open(sys.argv[1], "rt", encoding="utf-8") as points:
        for line in points:
            entry = json.loads(line)
            if entry.get("type") != "Point":
                continue
            data = entry["data"]
            minute = datetime.fromisoformat(data["time"]).strftime("%H:%M")
            if entry["metric"] == "http_reqs":
                requests[minute] += 1
            elif entry["metric"] == "http_req_failed":
                failures[minute] += int(data["value"])
            elif entry["metric"] == "http_req_duration" and data["tags"].get("type") == "search":
                search[minute].append(data["value"])
    print("dakika (UTC)  istek  hata %   arama p95 (ms)")
    for minute in sorted(requests):
        rate = 100 * failures[minute] / requests[minute]
        print(f"{minute}        {requests[minute]:6}  {rate:6.2f}   {percentile(search[minute], 0.95):8.1f}")


if __name__ == "__main__":
    main()
