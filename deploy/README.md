# Yerel Geliştirme Ortamı

Bu doküman, uygulamanın bütün bileşenleriyle (PostgreSQL, Elasticsearch, MinIO, Keycloak, API, frontend, işçi) yerel bir Kubernetes kümesinde, boş bir Ubuntu bilgisayarda sıfırdan nasıl kurulacağını anlatır. Kararların gerekçeleri ADR-0018'dedir.

Bilgisayarda Java, Node.js veya Python kurmak gerekmez: API, frontend ve işçi imajları Docker'ın içinde derlenir. Bunlar yalnızca testleri bilgisayarda çalıştırmak için gerekir.

## Donanım

| | En az | Önerilen | Not |
|---|---|---|---|
| Bellek (RAM) | 8 GB | 16 GB | Küme çalışırken yaklaşık 4,3 GB kullanır (Elasticsearch 1,75 GB, Keycloak 750 MB, API 200 MB); imaj derlemeleri sırasında ek bellek gerekir |
| Boş disk | 25 GB | 40 GB | İmajlar, derleme önbelleği ve veriler yaklaşık 20 GB tutar |
| İşlemci | 4 çekirdek | — | |
| İşletim sistemi | Ubuntu (64 bit, x86_64) | | Komutlar Ubuntu içindir |
| İnternet | Gerekli | | İmajlar ve bağımlılıklar indirilir; işçi haberleri kaynak sitelerden toplar |

İlk kurulumda imajların indirilmesi ve ilk derlemeler (Maven ve npm bağımlılıkları) internet hızına göre uzun sürebilir.

## Gereksinimler

| Araç | Sürüm | Not |
|---|---|---|
| Docker Engine | — | Kullanıcının `docker` grubunda olması gerekir |
| kubectl | 1.36.x | Kubernetes'in resmi paket deposundan (`pkgs.k8s.io`, v1.36 serisi) |
| Helm | 4.3.1 | `https://github.com/helm/helm/releases`; indirilen dosyanın özeti doğrulanmalıdır |
| k3d | 5.9.0 | `https://github.com/k3d-io/k3d/releases`; indirilen dosyanın özeti doğrulanmalıdır |
| git, curl, openssl | — | Depoyu indirmek, adresleri denemek ve şifre üretmek için |

### Araçların kurulumu (Ubuntu)

Araçlar kuruluysa bu bölüm atlanır; `docker version`, `kubectl version --client`, `helm version` ve `k3d version` komutlarıyla kontrol edilir.

**Temel araçlar:**

```bash
sudo apt update
sudo apt install -y git curl openssl ca-certificates gnupg
```

**Docker Engine** (Docker'ın resmi paket deposundan; adımlar `docs.docker.com/engine/install/ubuntu/` sayfasındakilerdir):

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# docker komutunu sudo olmadan çalıştırmak için kullanıcı docker grubuna eklenir.
sudo usermod -aG docker $USER
```

Grup üyeliğinin geçerli olması için **oturumu kapatıp yeniden açın** (veya bilgisayarı yeniden başlatın). Ardından `docker run --rm hello-world` sudo olmadan çalışmalıdır.

**kubectl** (Kubernetes'in resmi paket deposundan, v1.36 serisi; `kubernetes.io/docs/tasks/tools/install-kubectl-linux/`):

```bash
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.36/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
sudo chmod 644 /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.36/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo chmod 644 /etc/apt/sources.list.d/kubernetes.list
sudo apt update
sudo apt install -y kubectl
```

**Helm 4.3.1** (hazır derlenmiş dosya; özet doğrulanır):

```bash
cd /tmp
curl -fsSLO https://get.helm.sh/helm-v4.3.1-linux-amd64.tar.gz
curl -fsSLO https://get.helm.sh/helm-v4.3.1-linux-amd64.tar.gz.sha256sum
sha256sum -c helm-v4.3.1-linux-amd64.tar.gz.sha256sum   # "OK" yazmalı
tar -xzf helm-v4.3.1-linux-amd64.tar.gz
sudo install -m 0755 linux-amd64/helm /usr/local/bin/helm
helm version
```

**k3d 5.9.0** (hazır derlenmiş dosya; özet doğrulanır):

```bash
cd /tmp
curl -fsSLO https://github.com/k3d-io/k3d/releases/download/v5.9.0/k3d-linux-amd64
curl -fsSLO https://github.com/k3d-io/k3d/releases/download/v5.9.0/checksums.txt
# Özet dosyasında dosyanın adı "_dist/k3d-linux-amd64" olarak geçer; yalnızca özet karşılaştırılır.
echo "$(grep 'k3d-linux-amd64$' checksums.txt | cut -d' ' -f1)  k3d-linux-amd64" | sha256sum -c   # "OK" yazmalı
sudo install -m 0755 k3d-linux-amd64 /usr/local/bin/k3d
k3d version
```

### Bilgisayarın ayarları

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

Bu komut hiçbir çıktı vermemelidir. Bir web sunucusu (örneğin Apache veya nginx) 80 numaralı portu kullanıyorsa kurulumdan önce durdurulur.

## Kurulum

### Depoyu indir

Depo özeldir: indirmek için GitHub hesabının depoya eklenmiş (collaborator) olması gerekir.

```bash
git clone https://github.com/FallErdem/haber-arama-platformu.git
cd haber-arama-platformu
```

Bundan sonraki bütün komutlar deponun kök klasöründen çalıştırılır.

Yalnızca kodda değişiklik yapıp commit atacaksanız, commit öncesi gizli bilgi kontrolü bir kez etkinleştirilir:

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

Şifreler ve görsel adreslerini imzalayan anahtar (`api-media-signing.env`) `deploy/k8s/overlays/dev/secrets/` klasörüne yazılır. Bu klasör depoya girmez. Betik var olan dosyalara dokunmaz; daha önce kurulmuş bir ortamda yeni bir gizli bilgi eklendiğinde yeniden çalıştırılır ve yalnızca eksik olanları üretir.

Aynı klasöre, ilk yöneticinin e-posta adresini içeren `api-settings.env` dosyası elle eklenir (ADR-0014). Bu adresle kaydolan ve e-postasını doğrulayan kullanıcı ilk girişinde yönetici olur. `YONETICI_EPOSTASI` yerine 10. adımda Keycloak'a kaydolurken kullanacağınız adresi yazın; e-postalar gerçekten gönderilmez, Mailpit'te görünür:

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

API betiğiyle aynı şekilde çalışır (`frontend/Dockerfile`). Yeni kurulan bir kümede `frontend` pod'u da bu adım çalıştırılana kadar `ImagePullBackOff` durumunda kalır. İlk yönetici 10. adımda oluşturulur.

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

### 10. İlk yöneticiyi oluştur ve uygulamayı aç

1. Mailpit'in arayüzünü açın (komut çalıştığı sürece açık kalır; ayrı bir terminalde bırakın):

   ```bash
   kubectl port-forward -n haber svc/mailpit 8025:8025
   ```

   Tarayıcıda `http://localhost:8025`.

2. Tarayıcıda `http://haber.localhost/` adresini açın ve "Giriş yap"a basın. Keycloak'ın giriş sayfasındaki kayıt bağlantısıyla, 4. adımda `api-settings.env` dosyasına yazdığınız e-posta adresiyle kaydolun (kullanıcı adı, ad, soyad ve e-posta).
3. Keycloak e-postanın doğrulanmasını ister. Mailpit'te gelen e-postadaki bağlantıya tıklayın; ardından şifrenizi belirleyin (en az 12 karakter, kullanıcı adı veya e-posta olamaz).
4. Uygulamaya dönülür. Bu e-postayla gelen ilk kullanıcı aktif yönetici olarak kaydedilir: üst menüde Arama, Kaydedilenler ve Yönetim görünür.

Başka bir adresle kaydolan kullanıcı "onay bekliyor" durumunda kalır; yönetici onu Yönetim → Kullanıcılar ekranından onaylar. Haberler, işçinin ilk turu bittikçe aramada görünmeye başlar (birkaç dakika).

### 11. Ölçümleri ve uyarıları kur

Prometheus, API'nin, işçinin ve Kubernetes'in ölçümlerini toplar; Alertmanager uyarıları e-postayla Mailpit'e gönderir (ADR-0018, 13. bölüm). Uyarı kuralları `alerting-rules.yml` dosyasındadır; kurulum komutu dosyayı chart'a verir.

```bash
helm upgrade --install prometheus oci://ghcr.io/prometheus-community/charts/prometheus --version 29.45.2 \
  --namespace monitoring --create-namespace -f deploy/k8s/platform/prometheus/values.yaml \
  --set-file 'ruleFiles.alerting-rules\.yml=deploy/k8s/platform/prometheus/alerting-rules.yml' --wait
```

Kural dosyası değiştiğinde aynı komut yeniden çalıştırılır; Prometheus kuralları yaklaşık bir dakika içinde kendisi yeniden yükler. Kurallar kümeye uygulanmadan önce test edilir:

```bash
docker run --rm -v "$PWD/deploy/k8s/platform/prometheus:/rules:ro" -w /rules \
  --entrypoint promtool quay.io/prometheus/prometheus:v3.16.0 test rules alerting-rules.test.yml
```

Uyarılar üç yerde görülür:

| Nerede | Nasıl açılır | Ne gösterir |
|---|---|---|
| Mailpit | `kubectl port-forward -n haber svc/mailpit 8025:8025`, ardından `http://localhost:8025` | Uyarı e-postaları (`[FIRING]`) ve uyarı kalkınca gelen `[RESOLVED]` e-postaları |
| Prometheus | `kubectl port-forward -n monitoring svc/prometheus-server 9090:80`, ardından `http://localhost:9090/alerts` | Kuralların anlık durumu (`inactive`, `pending`, `firing`); "Graph" sekmesinde ölçümlerin grafikleri |
| Alertmanager | `kubectl port-forward -n monitoring svc/prometheus-alertmanager 9093:9093`, ardından `http://localhost:9093` | Gönderilmekte olan uyarılar; bir uyarı geçici olarak susturulabilir |

### 12. Arama indeksini yeniden oluştur (yalnızca gerektiğinde)

İlk kurulumda gerekmez; işçi haberleri topladıkça arama indeksine kendisi yazar. İndeks yapısı değiştiğinde (yeni bir alan, başka bir analizör) veya PostgreSQL ile Elasticsearch arasında meta veri tutarsızlığı şüphesi olduğunda çalıştırılır:

```bash
./scripts/dev/reindex.sh
```

Betik işçiyi durdurur, belgeleri metinleriyle birlikte yeni bir nesle (`articles-g2-...`) kopyalar ve meta verilerini PostgreSQL'den yazar (haber metinlerinin tek kaydı Elasticsearch'tir, ADR-0019), `articles` takma adını yeni nesle taşır, eski neslin indekslerini siler ve işçiyi yeniden başlatır. Arama bu sırada kesilmez; yalnızca haber toplama bekler. İş başarısız olursa etkin nesil değişmez; betik yeniden çalıştırılabilir. Etkin nesil şu komutla görülür (takma adı taşıyan şablon):

```bash
export ES_PW=$(grep '^password=' deploy/k8s/overlays/dev/secrets/elasticsearch-news-worker.env | cut -d= -f2)
kubectl exec -n haber elasticsearch-0 -- curl -s -u "news_worker:$ES_PW" 'localhost:9200/_index_template/articles*?filter_path=index_templates.name'
```

### 13. Yedekler

PostgreSQL her gece 03:00'te, Elasticsearch 03:30'da (Türkiye saati) MinIO'daki `backups` kovasına kendiliğinden yedeklenir; yedekler 7 gün saklanır (ADR-0018, 14. bölüm). Geceyi beklemeden yedek almak için:

```bash
# PostgreSQL: CronJob'un kalıbından hemen bir Job üretilir.
kubectl create job -n haber --from=cronjob/postgres-backup postgres-backup-elle
kubectl logs -n haber job/postgres-backup-elle -c upload

# Elasticsearch: gece politikası bir kez çalıştırılır ve snapshot'lar listelenir.
export ES_ELASTIC_PW=$(grep '^password=' deploy/k8s/overlays/dev/secrets/elasticsearch-elastic.env | cut -d= -f2)
kubectl exec -n haber elasticsearch-0 -c elasticsearch -- curl -s -u "elastic:$ES_ELASTIC_PW" -X POST 'localhost:9200/_slm/policy/nightly/_execute'
kubectl exec -n haber elasticsearch-0 -c elasticsearch -- curl -s -u "elastic:$ES_ELASTIC_PW" 'localhost:9200/_cat/snapshots/backups?v'
```

Geri dönüş denemesinin adımları ve sonucu: `docs/test-raporlari/2026-11-23-yedekten-geri-donus.md`.

### 14. Hacim testi deneme verisi (yalnızca gerektiğinde)

Hacim testi (FOG-07) için 1 milyon haber ve 10 milyon audit kaydı üretilir (`docs/05-veri-modeli.md`, 9. bölüm).

1. Yönetim panelinde kapalı bir kaynak oluşturun: kod `DENEME`, ana sayfa `https://deneme.invalid/`. Kaynak kapalıyken ona bir besleme ekleyin (`https://deneme.invalid/rss`); kapalı kaynağı işçi okumaz.
2. Haberleri ve audit kayıtlarını üretin:

   ```bash
   kubectl create job -n haber --from=cronjob/worker-volume-data worker-volume-data-1
   kubectl logs -n haber job/worker-volume-data-1 -f
   kubectl exec -i -n haber postgres-1 -c postgres -- psql -U postgres -d news -v ON_ERROR_STOP=1 \
     < scripts/dev/volume-data/audit-generate.sql
   ```

   Haberler gerçek toplama yolundan kaydedilir; outbox aktarımı onları Elasticsearch'e yazar. 24 Kasım 2026'da yazma 12,5 dakika, aktarım 30 dakika sürdü (aktarım süresi V18 indeksinden önce ölçüldü). Haber işi yarıda kalırsa yeni bir adla yeniden başlatılır; kayıtlı haberler atlanır.
3. Test bitince temizleyin: yönetim panelinde `DENEME` kaynağının içeriğini silin ("İçeriği sil"), ardından audit kayıtlarının geçici bölümlerini silin:

   ```bash
   kubectl exec -i -n haber postgres-1 -c postgres -- psql -U postgres -d news -v ON_ERROR_STOP=1 \
     < scripts/dev/volume-data/audit-remove.sql
   ```

## Doğrulama

| Ne | Komut | Beklenen |
|---|---|---|
| PostgreSQL | `kubectl get cluster -n haber` | `Cluster in healthy state` |
| Elasticsearch kullanıcıları ve snapshot politikası | `kubectl logs -n haber job/elasticsearch-setup` | "Roller, kullanıcılar ve snapshot politikası oluşturuldu." |
| MinIO kullanıcıları | `kubectl logs -n haber job/minio-setup` | "Kovalar, politikalar ve kullanıcılar oluşturuldu." |
| PostgreSQL yedeği | `kubectl get cronjob -n haber postgres-backup` | `SCHEDULE` sütununda `0 3 * * *` (her gece 03:00, Türkiye saati) |
| Keycloak | `curl -s -o /dev/null -w "%{http_code}\n" http://haber.localhost/auth/` | `302` |
| API | `curl -s -o /dev/null -w "%{http_code}\n" http://haber.localhost/api/v1/me` | `401` (token olmadan) |
| Frontend | `curl -s -o /dev/null -w "%{http_code}\n" http://haber.localhost/` | `200` |
| İşçi | `kubectl logs -n haber deploy/worker --tail=5` | "Okuma zamanı gelmiş besleme sayısı: ..." ve "Besleme toplandı: ... (yeni: ..., tekrar: ..., atlanan: ...)" satırları |
| Outbox aktarımı | `kubectl logs -n haber deploy/worker --tail=200 \| grep Outbox` | "Outbox aktarıldı (not: ..., yazılan haber: ..., metniyle yazılan: ..., silinen haber: ..., hata: 0)" satırları; Elasticsearch kapalıyken "Elasticsearch'e ulaşılamadı; outbox notları bekliyor" |
| Görsel indirme | `kubectl logs -n haber deploy/worker --tail=200 \| grep Görseller` | "Görseller işlendi (indirilen: ..., yeniden denenecek: ..., başarısız: ...)" satırları; MinIO kapalıyken "Nesne depolamaya ulaşılamadı; görseller bekliyor" |
| Prometheus'un okuduğu yerler | `kubectl get --raw '/api/v1/namespaces/monitoring/services/prometheus-server:80/proxy/api/v1/targets' \| grep -o '"health":"[a-z]*"' \| sort \| uniq -c` | Hepsi `"health":"up"` (API, işçi, Traefik, Kubernetes ve Prometheus'un kendisi) |
| API sağlık adresi dışarıya kapalı | `curl -s -o /dev/null -w "%{content_type}\n" http://haber.localhost/actuator/health` | `text/html` (yanıtı API değil frontend verir; API'nin yanıtı `application/...json` olurdu) |

Keycloak'ın yönetim paneli: `http://haber.localhost/auth/admin/`. Kullanıcı adı ve şifre `deploy/k8s/overlays/dev/secrets/keycloak-admin.env` dosyasındadır.

Mailpit'in arayüzü:

```bash
kubectl port-forward -n haber svc/mailpit 8025:8025
```

Ardından `http://localhost:8025`.

## Sorun giderme

| Belirti | Neden ve çözüm |
|---|---|
| `permission denied while trying to connect to the Docker daemon socket` | Kullanıcı `docker` grubuna eklendikten sonra oturum yeniden açılmamıştır. Oturumu kapatıp açın. |
| `k3d cluster create` port hatası veriyor (`address already in use`) | 80, 443 veya 5000 numaralı port başka bir program tarafından kullanılıyor. `ss -ltnp \| grep -E ':(80\|443\|5000)\b'` ile bulun ve durdurun. |
| `elasticsearch-0` pod'u sürekli yeniden başlıyor | `vm.max_map_count` değeri düşüktür (bkz. "Bilgisayarın ayarları"). |
| `api`, `frontend` veya `worker` pod'u `ImagePullBackOff` durumunda | O bileşenin imajı henüz derlenmemiştir. 7, 8 ve 9. adımlardaki betikler çalıştırılınca düzelir. |
| Pod'lar uzun süre `Pending` veya `ContainerCreating` durumunda | İlk kurulumda imajlar indiriliyordur; `kubectl describe pod -n haber <pod adı>` en alttaki olaylarda nedeni gösterir. Bellek yetersizse pod'lar `Pending` kalır. |
| `http://haber.localhost/` açılmıyor | `kubectl get pods -n haber` ile bütün pod'ların `Running` olduğunu, `kubectl get gateway -n traefik` ile ağ geçidinin `PROGRAMMED` olduğunu kontrol edin. |
| Giriş sayfasında e-posta doğrulaması bekleniyor ama e-posta yok | E-postalar gerçekten gönderilmez, Mailpit'e düşer; 10. adımdaki port yönlendirmesinin açık olduğunu kontrol edin. |
| İlk kullanıcı yönetici olmadı, "onay bekliyor" ekranı görünüyor | Kaydolunan adres `api-settings.env` dosyasındakiyle aynı değildir ya da dosya API dağıtıldıktan sonra eklenmiştir. Dosyayı düzeltip `kubectl apply -k deploy/k8s/overlays/dev` ve `kubectl rollout restart -n haber deployment/api` çalıştırın; kayıtlı kullanıcının rolü değişmez, yeni bir hesapla kaydolun. |
| Aramada hiç haber yok | İşçinin ilk turu sürüyordur veya pod internete çıkamıyordur: `kubectl logs -n haber deploy/worker --tail=20`. |
| `kubectl port-forward` bağlantısı kopuyor | Komut yeniden çalıştırılır; kopma kümeyi etkilemez. |

## Kümeyi silme

```bash
k3d cluster delete haber
```

Kümedeki **bütün veriler silinir.** Şifre dosyaları bilgisayarda kalır; küme yeniden kurulduğunda aynı şifreler kullanılır.