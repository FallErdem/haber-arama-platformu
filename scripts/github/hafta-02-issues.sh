#!/usr/bin/env bash
# Hafta 2 iş kalemlerini (docs/09-is-plani.md, İ-01 – İ-12) GitHub issue olarak açar.
set -euo pipefail

MILESTONE="Hafta 2"

create_issue() {
  local title="$1"
  local labels="$2"
  gh issue create --title "$title" --label "$labels" --milestone "$MILESTONE" --body-file -
}

create_issue "İ-01 Kalan teknik kararlar" "docs,altyapi,must" <<'EOF'
## Amaç

Çalışan iskeletten önce verilmesi gereken kararların verilmesi.

## Kararlar

- [ ] Frontend mimarisi: derleme aracı, durum yönetimi, yönlendirme, çeviri altyapısı
- [ ] Yerel Kubernetes ortamı
- [ ] MinIO'nun kurulum yöntemi
- [ ] Veritabanı geçiş aracı
- [ ] Modül sınırı denetimi
- [ ] CI tarama araçları

## Kabul ölçütleri

- Her karar gerekçesi ve alternatifleriyle ilgili dokümana veya ADR'ye yazıldı.
EOF

create_issue "İ-02 Kodlama standartları dokümanı" "docs,altyapi,must" <<'EOF'
## Amaç

OOP ve clean code ilkelerinin, Java ve Python için kuralların ve stil araçlarının belirlenmesi.

## Gereksinimler

FOG-28

## Kabul ölçütleri

- Kodlama standartları dokümanı depoda.
EOF

create_issue "İ-03 Yerel Kubernetes ortamı ve altyapı bileşenleri" "chore,altyapi,must" <<'EOF'
## Amaç

PostgreSQL, Elasticsearch, MinIO, Keycloak ve Mailpit'in yerel Kubernetes'te çalışması.

## Bağımlılık

İ-01

## Kabul ölçütleri

- Bütün bileşenler çalışıyor ve erişilebilir.
- PostgreSQL'de uygulama ve Keycloak veritabanları ile `news_owner`, `news_app`, `news_worker` ve `keycloak` kullanıcıları oluşturuldu.
- Kurulum adımları dokümante edildi.
EOF

create_issue "İ-04 Veritabanı geçiş betikleri" "feat,backend,must" <<'EOF'
## Amaç

`05-veri-modeli.md`'deki bütün tabloların geçiş betikleriyle oluşturulması.

## Gereksinimler

FOG-25

## Bağımlılık

İ-01

## Kabul ölçütleri

- Bütün tablolar, kısıtlar ve indeksler oluşturuldu.
- Audit bölümleri ve güncelleme ile silmeyi reddeden tetikleyici oluşturuldu.
- Kategoriler, kaynaklar ve beslemelerin başlangıç verisi eklendi.
- Veritabanı kullanıcılarının yetkileri tanımlandı.
- Betiklerin boş bir veritabanında hatasız çalıştığı test edildi.
EOF

create_issue "İ-05 Keycloak realm yapılandırması" "chore,altyapi,must" <<'EOF'
## Amaç

Uygulamanın Keycloak realm'inin yapılandırılması.

## Gereksinimler

FG-KY-01

## Bağımlılık

İ-03

## Kabul ölçütleri

- Realm, frontend istemcisi ve API için hedef kitle (`aud`) tanımlandı.
- Kendi kendine kayıt ve zorunlu e-posta doğrulaması açık; e-postalar Mailpit'e gidiyor.
- Olay kayıtları açık.
- Token'da oturum kimliğinin (`sid`) bulunduğu ve Türkçe dil seçeneği doğrulandı.
- Realm yapılandırması depoda, yeniden kurulabilir halde.
EOF

create_issue "İ-06 Spring Boot iskeleti" "feat,backend,must" <<'EOF'
## Amaç

API'nin iskeleti: modüller, JWT doğrulaması, kullanıcı eşleştirme ve durum kontrolü.

## Gereksinimler

FG-KY-02 – FG-KY-07, FOG-19, FOG-27, FOG-39

## Bağımlılık

İ-03, İ-04, İ-05

## Kabul ölçütleri

- Modül yapısı kuruldu.
- JWT'ler `/certs` anahtarlarıyla doğrulanıyor; `iss` ve `aud` kontrol ediliyor.
- İlk istekte kullanıcı kaydı oluşturuluyor; ilk yönetici kuralı çalışıyor.
- `GET /api/v1/me` çalışıyor.
- Hata yanıtları RFC 9457 biçiminde; her yanıtta `X-Request-Id` var.
- Birim, entegrasyon ve API testleri yazıldı.
EOF

create_issue "İ-07 React iskeleti" "feat,frontend,must" <<'EOF'
## Amaç

Frontend'in iskeleti: Keycloak ile giriş ve hesap durumu ekranı.

## Gereksinimler

FG-KY-01, FOG-31

## Bağımlılık

İ-01, İ-05, İ-06

## Kabul ölçütleri

- Keycloak ile Authorization Code + PKCE girişi çalışıyor; token bellekte tutuluyor.
- `/me` yanıtına göre hesap durumu ekranı gösteriliyor.
- Çeviri altyapısı kuruldu; arayüz metinleri dil dosyalarında.
- Testler yazıldı.
EOF

create_issue "İ-08 Python işçisi iskeleti" "feat,backend,must" <<'EOF'
## Amaç

İşçinin iskeleti: proje yapısı, veritabanı bağlantısı, zamanlayıcı döngüsü ve sağlık uç noktası.

## Gereksinimler

FOG-13

## Bağımlılık

İ-03, İ-04

## Kabul ölçütleri

- uv ile proje ve kilit dosyası oluşturuldu.
- İşçi `news_worker` kullanıcısıyla veritabanına bağlanıyor.
- Zamanlayıcı döngüsü okuma zamanı gelmiş beslemeleri buluyor.
- Sağlık uç noktası çalışıyor.
- Testler yazıldı.
EOF

create_issue "İ-09 Temel CI" "chore,altyapi,must" <<'EOF'
## Amaç

Her PR'da ve `main`'e yapılan her gönderimde çalışan temel CI.

## Gereksinimler

FOG-17, FOG-18, FOG-23, FOG-24, FOG-28, FOG-29

## Bağımlılık

İ-06, İ-07, İ-08

## Kabul ölçütleri

- Derleme, testler, kapsam ölçümü ve kod stili denetimi; yol filtreleriyle.
- Commit mesajı denetimi; birleştirme commit'leri hariç.
- Gizli bilgi ve bağımlılık açığı taraması.
EOF

create_issue "İ-10 RSS ve Atom okuyucuları" "feat,backend,must" <<'EOF'
## Amaç

RSS ve Atom beslemelerinin okunup ortak yapıya çevrilmesi.

## Gereksinimler

FG-VT-01 – FG-VT-03, FG-VT-08, FG-VT-09, FOG-16

## Bağımlılık

İ-08

## Kabul ölçütleri

- Kaynak bazında alan eşlemesi çalışıyor (örneğin TRT'nin `<imageUrl>` alanı).
- Tarihler UTC'ye çevriliyor.
- HTML temizleniyor; içerikteki `<img>` etiketleri çıkarılıyor.
- Adresler normalleştiriliyor.
- Kaydedilmiş gerçek ve zararlı içerikli besleme örnekleriyle testler yazıldı.
EOF

create_issue "İ-11 Kategori eşlemesi" "feat,backend,must" <<'EOF'
## Amaç

Kaynak kategorilerinin ortak kategori listesine eşlenmesi.

## Gereksinimler

FG-VT-12, FG-VT-13

## Bağımlılık

İ-10

## Kabul ölçütleri

- Gerçek beslemelerdeki kategori değerleri toplandı; eşleme tabloları geçiş betiğiyle eklendi.
- Besleme düzeyinde ve haber düzeyinde eşleme çalışıyor.
- Hiçbir konu kategorisi atanamayan haber "Diğer"e atanıyor.
- Türkçe küçük harf dönüşümü testlerle doğrulandı.
EOF

create_issue "İ-12 Kaydetme ve toplama akışı" "feat,backend,must" <<'EOF'
## Amaç

Toplanan haberlerin kaydedilmesi, toplama kayıtları ve hata yönetimi.

## Gereksinimler

FG-VT-04 – FG-VT-06, FG-VT-10, FG-YP-07

## Bağımlılık

İ-10

## Kabul ölçütleri

- Tekrar eden haberler görmezden geliniyor; ilk gelen kalıyor.
- Haber, kategoriler, görsel kuyruğu ve outbox kayıtları tek işlemde yazılıyor.
- Her okuma `ingestion_runs`'a kaydediliyor.
- Başarısız okumalar yeniden deneniyor; art arda 5 hatada besleme otomatik devre dışı kalıyor ve audit kaydı yazılıyor.
- Kaynak başına ortak istek sınırlayıcısı, koşullu istekler ve robots.txt kuralları uygulanıyor.
- Testler yazıldı.
EOF

echo "Hafta 2 issue'ları oluşturuldu."