#!/usr/bin/env bash
# Bir performans testini k6 ile çalıştırır (İ-38, test stratejisi 6. bölüm).
# Kullanım: tests/performance/run.sh <load|spike|stress|scale|soak>   (soak için süre: DURATION_MINUTES, varsayılan 120)
#
# - k6 Docker'da, 2 çekirdek ve 1 GB bellekle sınırlı çalışır: yük aracı ile sistem aynı bilgisayarda olduğundan
#   kaynakları ayrılır (R-25).
# - İstekler bilgisayarın ağından, kullanıcının yaptığı gibi Gateway'e (Traefik) gider: http://haber.localhost.
# - Sonuçlar tests/performance/results/ altına yazılır (depoya girmez): özet (JSON) ve isteklerin zaman serisi.
set -euo pipefail

TEST="${1:?Test adı gerekli: load, spike, stress, scale veya soak}"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SECRETS_DIR="$REPO_ROOT/deploy/k8s/overlays/dev/secrets"
RESULTS_DIR="$REPO_ROOT/tests/performance/results"
STAMP="$TEST-$(date +%Y%m%d-%H%M)"
mkdir -p "$RESULTS_DIR"
# İstekler k3d'nin geliştirme yük dengeleyicisini (k3d-haber-serverlb, nginx) atlayıp doğrudan küme düğümüne,
# Traefik'e gider: dengeleyicinin nginx süreçleri en çok 1024 dosya tanıtıcısı açabiliyor ve ani yükte tıkanıyor
# (24 Kasım 2026 ani yük denemesi). Gerçek ortamda onun yerinde bağlantı sayısına göre ayarlanmış bir dengeleyici olur.
NODE_IP="$(docker inspect k3d-haber-server-0 --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')"

docker run --rm \
  --network host --add-host "haber.localhost:$NODE_IP" \
  --cpus 2 --memory 1g \
  --user "$(id -u):$(id -g)" \
  -v "$REPO_ROOT/tests/performance:/scripts:ro" \
  -v "$SECRETS_DIR/loadtest-users.env:/secrets/loadtest-users.env:ro" \
  -v "$RESULTS_DIR:/results" \
  grafana/k6:2.3.0 run \
  -e TEST="$TEST" -e DURATION_MINUTES="${DURATION_MINUTES:-120}" \
  --summary-export "/results/$STAMP-summary.json" \
  --out "json=/results/$STAMP-points.json.gz" \
  /scripts/scenario.js
