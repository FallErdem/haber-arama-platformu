#!/usr/bin/env bash
# Trivy'yi resmi imajından, sabit sürümle çalıştırır (ADR-0018). CI'da ve
# geliştirme bilgisayarında aynı şekilde kullanılır; Trivy'nin kurulu olması gerekmez.
#
# Kullanım: scripts/ci/trivy.sh <trivy komutu ve seçenekleri>
# Örnek:    scripts/ci/trivy.sh fs --scanners vuln /repo/worker/uv.lock
#
# Depo, konteynerin içinde /repo altında salt okunur olarak görünür.
set -euo pipefail

TRIVY_IMAGE="ghcr.io/aquasecurity/trivy:0.76.1"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# Açık veritabanı her çalıştırmada yeniden indirilmesin diye önbellek klasörü bağlanır.
CACHE_DIR="${TRIVY_CACHE_DIR:-$HOME/.cache/trivy-ci}"
mkdir -p "$CACHE_DIR"

# Docker soketi: Trivy'nin bu bilgisayarda derlenmiş imajları okuyabilmesi için.
docker run --rm \
  -v "$REPO_ROOT:/repo:ro" \
  -v "$CACHE_DIR:/root/.cache" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  "$TRIVY_IMAGE" "$@"
