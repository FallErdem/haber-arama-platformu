#!/usr/bin/env bash
# Geliştirme ortamının şifre dosyalarını oluşturur (deploy/k8s/overlays/dev/secrets/).
# Var olan dosyalara dokunmaz; böylece çalışan bir kümenin şifreleri yanlışlıkla değişmez.
set -euo pipefail

SECRETS_DIR="$(cd "$(dirname "$0")/../.." && pwd)/deploy/k8s/overlays/dev/secrets"
mkdir -p "$SECRETS_DIR"

# Oluşturulan dosyaları yalnızca dosyanın sahibi okuyabilir.
umask 077

create_secret() {
  local name="$1"
  local username="$2"
  local file="$SECRETS_DIR/$name.env"

  if [[ -f "$file" ]]; then
    echo "Var olduğu için atlandı: $name"
    return
  fi

  printf 'username=%s\npassword=%s\n' "$username" "$(openssl rand -hex 24)" > "$file"
  echo "Oluşturuldu: $name"
}

create_secret postgres-news-owner news_owner
create_secret postgres-news-app news_app
create_secret postgres-news-worker news_worker
create_secret postgres-keycloak keycloak
create_secret elasticsearch-elastic elastic
create_secret elasticsearch-news-worker news_worker
create_secret elasticsearch-news-api news_api
create_secret minio-root haber-admin
create_secret minio-news-worker news-worker
create_secret minio-news-api news-api
create_secret keycloak-admin haber-admin

# Kullanıcı adı ve şifre yerine tek bir anahtar taşıyan gizli bilgiler.
create_key() {
  local name="$1"
  local file="$SECRETS_DIR/$name.env"

  if [[ -f "$file" ]]; then
    echo "Var olduğu için atlandı: $name"
    return
  fi

  printf 'key=%s\n' "$(openssl rand -hex 32)" > "$file"
  echo "Oluşturuldu: $name"
}

# Görsel adreslerini imzalayan anahtar (API sözleşmesi 4.4); 64 karakter.
create_key api-media-signing
