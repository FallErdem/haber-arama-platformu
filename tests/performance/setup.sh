#!/usr/bin/env bash
# Performans testleri (İ-38) için Keycloak'ta geçici bir test client'ı ve 10 test kullanıcısı oluşturur,
# kullanıcıları uygulamaya bir kez giriş yaptırarak kaydettirir.
#
# - Client (`haber-loadtest`) yalnızca şifreyle doğrudan token almaya izin verir. Frontend client'ı buna kapalıdır ve
#   açılmaz; test aracı gerçek yapılandırmaya (realm-haber.json) girmez. Test bitince teardown.sh ile silinir.
# - Kullanıcılar (`yuktesti01` … `yuktesti10`) ortak bir şifre kullanır. Şifre secrets/loadtest-users.env dosyasında
#   tutulur (depoya girmez), komut satırına ve ekrana yazılmaz.
# - Kullanıcılar uygulamada "onay bekliyor" (PENDING) olarak kaydolur; yönetim panelinden onaylanmaları gerekir.
#
# Betik tekrar çalıştırılabilir: var olan client ve kullanıcılar yeniden oluşturulmaz.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SECRETS_DIR="$REPO_ROOT/deploy/k8s/overlays/dev/secrets"
PASSWORD_FILE="$SECRETS_DIR/loadtest-users.env"
BASE_URL="http://haber.localhost"
CLIENT_ID="haber-loadtest"
USER_COUNT=10

umask 077
if [[ ! -f "$PASSWORD_FILE" ]]; then
  # 32 karakter: realm'in şifre kuralı (en az 12 karakter, kullanıcı adı ve e-posta olamaz) karşılanır.
  printf 'password=%s\n' "$(openssl rand -hex 16)" > "$PASSWORD_FILE"
  echo "Test kullanıcılarının şifresi oluşturuldu: $PASSWORD_FILE"
fi

ADMIN_USER="$(grep '^username=' "$SECRETS_DIR/keycloak-admin.env" | cut -d= -f2)"
ADMIN_PASSWORD="$(grep '^password=' "$SECRETS_DIR/keycloak-admin.env" | cut -d= -f2)"
USER_PASSWORD="$(grep '^password=' "$PASSWORD_FILE" | cut -d= -f2)"

# Keycloak'ın yönetim komutu (kcadm) pod'un içinde çalışır. Şifreler stdin ile verilir; kubectl'in komut satırında
# görünmez. Komutların kendisi (aşağıdaki metin) gizli bilgi içermez. Client'ın hedef kitle (aud: haber-api)
# eşlemesi frontend client'ındakiyle aynıdır; API token'ı buna göre kabul eder.
# Not: Metin tek tırnak içindedir; içine kesme işareti yazılmamalı (tırnağı kapatır).
# shellcheck disable=SC2016  # $ işaretleri pod'daki kabukta açılır.
KCADM_SCRIPT='
set -euo pipefail
read -r ADMIN_USER
read -r ADMIN_PASSWORD
read -r USER_PASSWORD
kcadm() { /opt/keycloak/bin/kcadm.sh "$@" --config /tmp/kcadm-loadtest.config; }
kcadm config credentials --server http://localhost:8080/auth --realm master \
  --user "$ADMIN_USER" --password "$ADMIN_PASSWORD" > /dev/null

if [ -z "$(kcadm get clients -r haber -q clientId='"$CLIENT_ID"' --fields id --format csv --noquotes)" ]; then
  kcadm create clients -r haber \
    -s clientId='"$CLIENT_ID"' -s "name=Performans testi (geçici)" -s publicClient=true \
    -s standardFlowEnabled=false -s implicitFlowEnabled=false -s directAccessGrantsEnabled=true \
    -s serviceAccountsEnabled=false \
    -s '\''protocolMappers=[{"name":"haber-api-audience","protocol":"openid-connect","protocolMapper":"oidc-audience-mapper","config":{"included.custom.audience":"haber-api","access.token.claim":"true","id.token.claim":"false"}}]'\''
  echo "Client oluşturuldu: '"$CLIENT_ID"'"
fi

for number in $(seq -w 1 '"$USER_COUNT"'); do
  username="yuktesti$number"
  if [ -z "$(kcadm get users -r haber -q username="$username" -q exact=true --fields id --format csv --noquotes)" ]; then
    kcadm create users -r haber -s username="$username" -s enabled=true -s emailVerified=true \
      -s email="$username@example.test" -s firstName=Yuk -s lastName="Testi $number" > /dev/null
    echo "Kullanıcı oluşturuldu: $username"
  fi
  kcadm set-password -r haber --username "$username" --new-password "$USER_PASSWORD"
done
rm -f /tmp/kcadm-loadtest.config
'

printf '%s\n%s\n%s\n' "$ADMIN_USER" "$ADMIN_PASSWORD" "$USER_PASSWORD" |
  kubectl exec -i -n haber deploy/keycloak -- bash -c "$KCADM_SCRIPT"

# Her kullanıcı bir kez giriş yapar ve /api/v1/me'yi çağırır: uygulama kullanıcıyı ilk istekte kaydeder (ADR-0014).
echo "Uygulamadaki durumlar:"
for number in $(seq -w 1 "$USER_COUNT"); do
  username="yuktesti$number"
  # Şifre stdin'den okunur (--data-urlencode password@-); curl'ün komut satırında görünmez.
  token="$(printf '%s' "$USER_PASSWORD" | curl -sf "$BASE_URL/auth/realms/haber/protocol/openid-connect/token" \
    -d grant_type=password -d client_id="$CLIENT_ID" -d username="$username" --data-urlencode password@- |
    python3 -c 'import json, sys; print(json.load(sys.stdin)["access_token"])')"
  status="$(curl -s "$BASE_URL/api/v1/me" -H "Authorization: Bearer $token" |
    python3 -c 'import json, sys; body = json.load(sys.stdin); print(body.get("status") or body.get("code"))')"
  echo "  $username: $status"
done
echo "PENDING olan kullanıcıları yönetim panelinden (Yönetim → Kullanıcılar) onaylayın."
