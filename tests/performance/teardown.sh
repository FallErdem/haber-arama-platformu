#!/usr/bin/env bash
# Performans testlerinden sonra Keycloak'taki test client'ını (`haber-loadtest`) ve test kullanıcılarını siler.
# Uygulamadaki kullanıcı kayıtları (users tablosu) silinmez; audit kayıtları onlara bağlıdır. İstenirse yönetim
# panelinden pasif yapılır.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SECRETS_DIR="$REPO_ROOT/deploy/k8s/overlays/dev/secrets"
ADMIN_USER="$(grep '^username=' "$SECRETS_DIR/keycloak-admin.env" | cut -d= -f2)"
ADMIN_PASSWORD="$(grep '^password=' "$SECRETS_DIR/keycloak-admin.env" | cut -d= -f2)"

# shellcheck disable=SC2016  # $ işaretleri pod'daki kabukta açılır.
KCADM_SCRIPT='
set -euo pipefail
read -r ADMIN_USER
read -r ADMIN_PASSWORD
kcadm() { /opt/keycloak/bin/kcadm.sh "$@" --config /tmp/kcadm-loadtest.config; }
kcadm config credentials --server http://localhost:8080/auth --realm master \
  --user "$ADMIN_USER" --password "$ADMIN_PASSWORD" > /dev/null
for number in $(seq -w 1 10); do
  id="$(kcadm get users -r haber -q username="yuktesti$number" -q exact=true --fields id --format csv --noquotes)"
  if [ -n "$id" ]; then kcadm delete "users/$id" -r haber; echo "Kullanıcı silindi: yuktesti$number"; fi
done
id="$(kcadm get clients -r haber -q clientId=haber-loadtest --fields id --format csv --noquotes)"
if [ -n "$id" ]; then kcadm delete "clients/$id" -r haber; echo "Client silindi: haber-loadtest"; fi
rm -f /tmp/kcadm-loadtest.config
'

printf '%s\n%s\n' "$ADMIN_USER" "$ADMIN_PASSWORD" | kubectl exec -i -n haber deploy/keycloak -- bash -c "$KCADM_SCRIPT"
