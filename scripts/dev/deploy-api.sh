#!/usr/bin/env bash
# Spring Boot API'yi derler, yerel imaj deposuna gönderir ve kümeye dağıtır.
# İmajın etiketi o anki commit'in kısa özetidir; böylece kümede hangi kodun
# çalıştığı her zaman bellidir. Commit'lenmemiş değişiklik varsa etikete
# "-dirty" eklenir.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OVERLAY="$REPO_ROOT/deploy/k8s/overlays/dev"
IMAGE_NAME="newssearch-api"
# Aynı imaj deposunun iki adresi vardır: bilgisayardan 127.0.0.1:5000, kümenin
# içinden haber-registry.localhost:5000. Docker yalnızca 127.0.0.1 adresine
# şifresiz (HTTP) bağlanmayı kabul ettiği için gönderim bu adresle yapılır.
PUSH_IMAGE="127.0.0.1:5000/$IMAGE_NAME"

cd "$REPO_ROOT"

TAG="$(git rev-parse --short HEAD)"
if [[ -n "$(git status --porcelain -- backend db/migrations)" ]]; then
  TAG="$TAG-dirty"
fi

echo "İmaj derleniyor: $IMAGE_NAME:$TAG"
docker build -f backend/Dockerfile -t "$PUSH_IMAGE:$TAG" .
docker push "$PUSH_IMAGE:$TAG"

# Overlay'de yalnızca bu imajın etiketini değiştirir: imaj adının geçtiği satırı
# bulur ve hemen altındaki newTag satırını yeni etiketle yazar.
sed -i "/name: .*\/$IMAGE_NAME\$/{n;s|newTag: .*|newTag: $TAG|;}" "$OVERLAY/kustomization.yaml"

kubectl apply -k "$OVERLAY"
kubectl rollout status -n haber deployment/api --timeout=180s
