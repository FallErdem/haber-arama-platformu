#!/usr/bin/env bash
# Arama indeksini PostgreSQL'den baştan üretir (tam yeniden indeksleme, ADR-0012).
#
# Ne zaman: indeks yapısı değiştiğinde (yeni alan, başka analizör) veya PostgreSQL ile
# Elasticsearch arasında tutarsızlık şüphesi olduğunda.
#
# Adımlar: işçi durdurulur -> yeniden indeksleme Job'u çalışır -> işçi yeniden başlatılır.
# Arama bu sırada kesilmez (API eski indekslerden okur); yalnızca haber toplama bekler.
# İş başarılı biterse eski neslin indeksleri silinir; başarısız olursa hiçbir şey değişmez.
set -euo pipefail

NAMESPACE="haber"
JOB="worker-reindex-$(date +%Y%m%d-%H%M%S)"
TIMEOUT_SECONDS=1800

# Betik nasıl biterse bitsin (başarı, hata, Ctrl+C) işçi yeniden başlatılır.
trap 'echo "İşçi yeniden başlatılıyor"; kubectl scale -n "$NAMESPACE" deployment/worker --replicas=1' EXIT

echo "İşçi durduruluyor"
kubectl scale -n "$NAMESPACE" deployment/worker --replicas=0
# İşçi elindeki beslemeyi bitirip kapanır (en fazla 60 saniye, bkz. worker/deployment.yaml).
kubectl wait -n "$NAMESPACE" --for=delete pod -l app=worker --timeout=120s

echo "Yeniden indeksleme başlatılıyor: $JOB"
kubectl create job -n "$NAMESPACE" "$JOB" --from=cronjob/worker-reindex

# Job bitene kadar beklenir. "kubectl wait" tek bir koşul bekleyebildiği için (yalnızca başarı ya da
# yalnızca hata) durum burada yoklanır.
deadline=$((SECONDS + TIMEOUT_SECONDS))
result=""
while [[ -z "$result" ]]; do
  if [[ "$(kubectl get job -n "$NAMESPACE" "$JOB" -o jsonpath='{.status.succeeded}')" == "1" ]]; then
    result="succeeded"
  elif [[ -n "$(kubectl get job -n "$NAMESPACE" "$JOB" -o jsonpath='{.status.failed}')" ]]; then
    result="failed"
  elif ((SECONDS > deadline)); then
    result="timeout"
  else
    sleep 2
  fi
done

kubectl logs -n "$NAMESPACE" "job/$JOB" || true

if [[ "$result" != "succeeded" ]]; then
  echo "Yeniden indeksleme tamamlanamadı ($result). Etkin nesil değişmedi; arama eskisi gibi çalışıyor." >&2
  exit 1
fi
echo "Yeniden indeksleme tamamlandı."
