#!/usr/bin/env bash
# Python işçisini derler, yerel imaj deposuna gönderir ve kümeye dağıtır.
# İmajın etiketi o anki commit'in kısa özetidir; commit'lenmemiş değişiklik
# varsa etikete "-dirty" eklenir (bkz. deploy-api.sh).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OVERLAY="$REPO_ROOT/deploy/k8s/overlays/dev"
IMAGE_NAME="newssearch-worker"
# Docker yalnızca 127.0.0.1 adresine şifresiz (HTTP) bağlanmayı kabul eder; küme
# aynı imajı haber-registry.localhost:5000 adıyla çeker.
PUSH_IMAGE="127.0.0.1:5000/$IMAGE_NAME"

cd "$REPO_ROOT"

TAG="$(git rev-parse --short HEAD)"
if [[ -n "$(git status --porcelain -- worker)" ]]; then
  TAG="$TAG-dirty"
fi

echo "İmaj derleniyor: $IMAGE_NAME:$TAG"
docker build -f worker/Dockerfile -t "$PUSH_IMAGE:$TAG" .
docker push "$PUSH_IMAGE:$TAG"

# Overlay'de yalnızca bu imajın etiketini değiştirir: imaj adının geçtiği satırı
# bulur ve hemen altındaki newTag satırını yeni etiketle yazar.
sed -i "/name: .*\/$IMAGE_NAME\$/{n;s|newTag: .*|newTag: $TAG|;}" "$OVERLAY/kustomization.yaml"

kubectl apply -k "$OVERLAY"
kubectl rollout status -n haber deployment/worker --timeout=120s
