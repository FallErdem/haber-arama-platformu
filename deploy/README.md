# Yerel Geliştirme Ortamı

Bu doküman, uygulamanın altyapısının yerel bir Kubernetes kümesinde sıfırdan nasıl kurulacağını anlatır. Kararların gerekçeleri ADR-0018'dedir.

## Gereksinimler

| Araç | Sürüm | Not |
|---|---|---|
| Docker | — | Kullanıcının `docker` grubunda olması gerekir |
| kubectl | 1.36.x | Kubernetes'in resmi paket deposundan (`pkgs.k8s.io`, v1.36 serisi) |
| Helm | 4.3.1 | `https://github.com/helm/helm/releases`; indirilen dosyanın özeti doğrulanmalıdır |
| k3d | 5.9.0 | `https://github.com/k3d-io/k3d/releases`; indirilen dosyanın özeti doğrulanmalıdır |
| openssl | — | Şifre üretmek için |

Elasticsearch için bilgisayarın `vm.max_map_count` değerinin en az 262144 olması gerekir:

```bash
sysctl vm.max_map_count
```

Değer düşükse:

```bash
echo 'vm.max_map_count=262144' | sudo tee /etc/sysctl.d/99-elasticsearch.conf
sudo sysctl --system
```

Bilgisayarın 80, 443 ve 5000 numaralı portlarının boş olması gerekir:

```bash
ss -ltnp | grep -E ':(80|443|5000)\b'
```

Bu komut hiçbir çıktı vermemelidir.

## Kurulum

Bütün komutlar deponun kök klasöründen çalıştırılır.

### 1. Kümeyi oluştur

```bash
k3d cluster create --config deploy/k3d/haber-cluster.yaml
kubectl get nodes
```

Düğüm `Ready` durumunda olmalıdır.

### 2. Gateway API ve Traefik

```bash
kubectl apply --server-side -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.6.3/standard-install.yaml

helm repo add traefik https://traefik.github.io/charts
helm repo update
helm upgrade --install traefik traefik/traefik --version 42.3.1 \
  --namespace traefik --create-namespace \
  -f deploy/k8s/platform/traefik/values.yaml --wait

kubectl get gateway -n traefik
```

`traefik-gateway`'in `PROGRAMMED` sütunu `True` olmalıdır.

### 3. CloudNativePG operatörü

```bash
helm repo add cnpg https://cloudnative-pg.github.io/charts
helm repo update
helm upgrade --install cnpg cnpg/cloudnative-pg --version 0.29.1 \
  --namespace cnpg-system --create-namespace --wait
```

### 4. Şifreleri oluştur

```bash
./scripts/dev/generate-secrets.sh
```

Şifreler `deploy/k8s/overlays/dev/secrets/` klasörüne yazılır. Bu klasör depoya girmez.

### 5. `haber.local` adresini tanıt

```bash
echo '127.0.0.1 haber.local' | sudo tee -a /etc/hosts
```

### 6. Bileşenleri kur

```bash
kubectl apply -k deploy/k8s/overlays/dev
kubectl get pods -n haber -w
```

Bütün pod'lar `Running`, kurulum işlerinin (`elasticsearch-setup`, `minio-setup`) pod'ları `Completed` olmalıdır. İlk kurulumda imajların indirilmesi birkaç dakika sürebilir.

## Doğrulama

| Ne | Komut | Beklenen |
|---|---|---|
| PostgreSQL | `kubectl get cluster -n haber` | `Cluster in healthy state` |
| Elasticsearch kullanıcıları | `kubectl logs -n haber job/elasticsearch-setup` | "Roller ve kullanıcılar oluşturuldu." |
| MinIO kullanıcıları | `kubectl logs -n haber job/minio-setup` | "Kova, politikalar ve kullanıcılar oluşturuldu." |
| Keycloak | `curl -s -o /dev/null -w "%{http_code}\n" http://haber.local/auth/` | `302` |

Keycloak'ın yönetim paneli: `http://haber.local/auth/admin/`. Kullanıcı adı ve şifre `deploy/k8s/overlays/dev/secrets/keycloak-admin.env` dosyasındadır.

Mailpit'in arayüzü:

```bash
kubectl port-forward -n haber svc/mailpit 8025:8025
```

Ardından `http://localhost:8025`.

## Kümeyi silme

```bash
k3d cluster delete haber
```

Kümedeki **bütün veriler silinir.** Şifre dosyaları bilgisayarda kalır; küme yeniden kurulduğunda aynı şifreler kullanılır.