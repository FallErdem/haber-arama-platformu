#!/usr/bin/env bash
# Spring Boot API'yi derler, yerel imaj deposuna gönderir ve kümeye dağıtır.
# İmajın etiketi o anki commit'in kısa özetidir; böylece kümede hangi kodun
# çalıştığı her zaman bellidir. Commit'lenmemiş değişiklik varsa etikete
# "-dirty" eklenir.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OVERLAY="$REPO_ROOT/deploy/k8s/overlays/dev"
IMAGE="haber-registry.localhost:5000/newssearch-api"

cd "$REPO_ROOT"

TAG="$(git rev-parse --short HEAD)"
if [[ -n "$(git status --porcelain -- backend db/migrations)" ]]; then
  TAG="$TAG-dirty"
fi

echo "İmaj derleniyor: $IMAGE:$TAG"
docker build -f backend/Dockerfile -t "$IMAGE:$TAG" .
docker push "$IMAGE:$TAG"

# Overlay'deki etiket satırını yeni etiketle değiştirir.
sed -i "s|^\(    newTag: \).*|\1$TAG|" "$OVERLAY/kustomization.yaml"

kubectl apply -k "$OVERLAY"
kubectl rollout status -n haber deployment/api --timeout=180s
