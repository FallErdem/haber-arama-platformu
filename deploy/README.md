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

Depo ilk indirildiğinde, commit öncesi gizli bilgi kontrolü bir kez etkinleştirilir:

```bash
git config core.hooksPath .githooks
```

Bundan sonra her `git commit`, commit'e eklenen değişiklikleri gitleaks ile tarar ve parola, token veya API anahtarına benzeyen bir değer bulursa commit'i durdurur. Kontrol Docker'ı kullanır.

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

Aynı klasöre, ilk yöneticinin e-posta adresini içeren `api-settings.env` dosyası elle eklenir (ADR-0014). Bu adresle kaydolan ve e-postasını doğrulayan kullanıcı ilk girişinde yönetici olur:

```bash
printf 'initial-admin-email=%s\n' 'YONETICI_EPOSTASI' > deploy/k8s/overlays/dev/secrets/api-settings.env
chmod 600 deploy/k8s/overlays/dev/secrets/api-settings.env
```

### 5. `haber.localhost` adresi

Uygulamaya `http://haber.localhost` adresinden erişilir. `.localhost` ile biten adresler kendiliğinden bu bilgisayarı gösterir; `/etc/hosts` dosyasına kayıt eklemek gerekmez.

Adresin `.localhost` ile bitmesi bilinçli bir seçimdir: Tarayıcılar, girişte kullanılan PKCE'nin gerektirdiği şifreleme işlevlerini yalnızca HTTPS adreslerinde ve `localhost` adreslerinde açar. HTTPS gelene kadar (İ-32) giriş bu sayede çalışır.

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://haber.localhost/
```

Küme kuruluysa bir HTTP durum kodu döner (bileşenler kurulmadan önce `404`).

### 6. Bileşenleri kur

```bash
kubectl apply -k deploy/k8s/overlays/dev
kubectl get pods -n haber -w
```

Bütün pod'lar `Running`, kurulum işlerinin (`elasticsearch-setup`, `minio-setup`) pod'ları `Completed` olmalıdır. İlk kurulumda imajların indirilmesi birkaç dakika sürebilir.

### 7. API'yi derle ve dağıt

```bash
./scripts/dev/deploy-api.sh
```

Betik API imajını derler (`backend/Dockerfile`, derleme bağlamı deponun kökü), yerel imaj deposuna gönderir, `deploy/k8s/overlays/dev/kustomization.yaml` dosyasındaki imaj etiketini günceller ve kümeye uygular. Etiket, o anki commit'in kısa özetidir; commit'lenmemiş değişiklik varsa sonuna `-dirty` eklenir. API kodunda yapılan her değişiklikten sonra aynı betik yeniden çalıştırılır.

İmaj bilgisayardan `127.0.0.1:5000` adresine gönderilir; küme aynı imajı `haber-registry.localhost:5000` adıyla çeker.

### 8. Frontend'i derle ve dağıt

```bash
./scripts/dev/deploy-frontend.sh
```

API betiğiyle aynı şekilde çalışır (`frontend/Dockerfile`). Yeni kurulan bir kümede `frontend` pod'u da bu adım çalıştırılana kadar `ImagePullBackOff` durumunda kalır.

Ardından tarayıcıda `http://haber.localhost/` adresi açılır. "Giriş yap" Keycloak'ın giriş sayfasına götürür; ilk kullanıcı oradaki kayıt bağlantısıyla oluşturulur. Doğrulama e-postası Mailpit'e düşer.

### 9. İşçiyi derle ve dağıt

```bash
./scripts/dev/deploy-worker.sh
```

Diğer iki betikle aynı şekilde çalışır (`worker/Dockerfile`). İşçi, tabloları API kurduğu için API'den sonra dağıtılır; önce dağıtılırsa çökmez, tablolar hazır olana kadar bekler.

İşçi başladığında okuma zamanı gelmiş beslemeleri kaynak sitelerden toplamaya başlar; bunun için pod'un internete çıkabilmesi gerekir. Yeni bir veritabanında 42 beslemenin hepsinin zamanı gelmiş olduğundan ilk tur, kaynak başına istek aralıkları nedeniyle birkaç dakika sürer.

İsteğe bağlı ayarlar (ortam değişkenleri; verilmezse varsayılan kullanılır):

| Değişken | Varsayılan | Anlamı |
|---|---|---|
| `HTTP_USER_AGENT` | `HaberAramaPlatformu/0.1 (egitim projesi)` | İşçinin kaynak sitelere kendini tanıttığı ad |
| `HTTP_TIMEOUT_SECONDS` | `10` | Bir isteğin her aşaması için süre sınırı |
| `HTTP_TOTAL_TIMEOUT_SECONDS` | `30` | Bir indirmenin toplam süre sınırı |
| `SCHEDULER_INTERVAL_SECONDS` | `30` | Zamanlayıcının iki turu arasındaki süre |
| `OUTBOX_INTERVAL_SECONDS` | `5` | Outbox aktarımının iki turu arasındaki süre |
| `OUTBOX_BATCH_SIZE` | `200` | Bir turda Elasticsearch'e aktarılan en fazla outbox notu |
| `ES_TIMEOUT_SECONDS` | `30` | Elasticsearch'e giden bir isteğin süre sınırı |
| `MEDIA_INTERVAL_SECONDS` | `10` | Görsel indirme döngüsünün iki turu arasındaki süre |
| `MEDIA_BATCH_SIZE` | `100` | Bir turda alınan en fazla görsel |

### 10. Arama indeksini yeniden oluştur (yalnızca gerektiğinde)

İlk kurulumda gerekmez; işçi haberleri topladıkça arama indeksine kendisi yazar. İndeks yapısı değiştiğinde (yeni bir alan, başka bir analizör) veya PostgreSQL ile Elasticsearch arasında tutarsızlık şüphesi olduğunda çalıştırılır:

```bash
./scripts/dev/reindex.sh
```

Betik işçiyi durdurur, bütün haberleri yeni bir nesle (`articles-g2-...`) yazar, `articles` takma adını oraya taşır, eski neslin indekslerini siler ve işçiyi yeniden başlatır. Arama bu sırada kesilmez; yalnızca haber toplama bekler. İş başarısız olursa etkin nesil değişmez; betik yeniden çalıştırılabilir. Etkin nesil şu komutla görülür (takma adı taşıyan şablon):

```bash
export ES_PW=$(grep '^password=' deploy/k8s/overlays/dev/secrets/elasticsearch-news-worker.env | cut -d= -f2)
kubectl exec -n haber elasticsearch-0 -- curl -s -u "news_worker:$ES_PW" 'localhost:9200/_index_template/articles*?filter_path=index_templates.name'
```

## Doğrulama

| Ne | Komut | Beklenen |
|---|---|---|
| PostgreSQL | `kubectl get cluster -n haber` | `Cluster in healthy state` |
| Elasticsearch kullanıcıları | `kubectl logs -n haber job/elasticsearch-setup` | "Roller ve kullanıcılar oluşturuldu." |
| MinIO kullanıcıları | `kubectl logs -n haber job/minio-setup` | "Kova, politikalar ve kullanıcılar oluşturuldu." |
| Keycloak | `curl -s -o /dev/null -w "%{http_code}\n" http://haber.localhost/auth/` | `302` |
| API | `curl -s -o /dev/null -w "%{http_code}\n" http://haber.localhost/api/v1/me` | `401` (token olmadan) |
| Frontend | `curl -s -o /dev/null -w "%{http_code}\n" http://haber.localhost/` | `200` |
| İşçi | `kubectl logs -n haber deploy/worker --tail=5` | "Okuma zamanı gelmiş besleme sayısı: ..." ve "Besleme toplandı: ... (yeni: ..., tekrar: ..., atlanan: ...)" satırları |
| Outbox aktarımı | `kubectl logs -n haber deploy/worker --tail=200 \| grep Outbox` | "Outbox aktarıldı (not: ..., yazılan haber: ..., silinen haber: ..., hata: 0)" satırları; Elasticsearch kapalıyken "Elasticsearch'e ulaşılamadı; outbox notları bekliyor" |
| API sağlık adresi dışarıya kapalı | `curl -s -o /dev/null -w "%{content_type}\n" http://haber.localhost/actuator/health` | `text/html` (yanıtı API değil frontend verir; API'nin yanıtı `application/...json` olurdu) |

Keycloak'ın yönetim paneli: `http://haber.localhost/auth/admin/`. Kullanıcı adı ve şifre `deploy/k8s/overlays/dev/secrets/keycloak-admin.env` dosyasındadır.

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