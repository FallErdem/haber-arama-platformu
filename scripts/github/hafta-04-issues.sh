#!/usr/bin/env bash
# Hafta 4 iş kalemlerini (docs/09-is-plani.md, İ-32 – İ-41) GitHub issue olarak açar.
# "Hafta 4" ve "Zaman kalırsa" kilometre taşları yoksa önce onları oluşturur. Ardından Hafta 3'ten
# taşınan İ-13'ü Hafta 4'e, "zaman kalırsa" olarak bırakılan İ-28 – İ-31'i "Zaman kalırsa"ya taşır.
set -euo pipefail

MILESTONE="Hafta 4"
MILESTONE_DUE="2026-11-27T00:00:00Z"
LATER="Zaman kalırsa"

milestone_exists() {
  gh api "repos/{owner}/{repo}/milestones?state=all" --jq '.[].title' | grep -qx "$1"
}

# Kilometre taşı varsa yeniden oluşturulmaz; betik bu adımda hata vermeden devam eder.
if ! milestone_exists "$MILESTONE"; then
  gh api "repos/{owner}/{repo}/milestones" -f title="$MILESTONE" -f due_on="$MILESTONE_DUE" --silent
  echo "Kilometre taşı oluşturuldu: $MILESTONE"
fi
if ! milestone_exists "$LATER"; then
  gh api "repos/{owner}/{repo}/milestones" -f title="$LATER" --silent
  echo "Kilometre taşı oluşturuldu: $LATER"
fi

create_issue() {
  local title="$1"
  local labels="$2"
  gh issue create --title "$title" --label "$labels" --milestone "$MILESTONE" --body-file -
}

# Açık bir issue'yu başlığının başındaki kimlikle ("İ-13") bulur ve verilen kilometre taşına taşır.
move_issue() {
  local id="$1"
  local milestone="$2"
  local number
  number=$(gh issue list --state open --limit 100 --json number,title \
    --jq ".[] | select(.title | startswith(\"$id \")) | .number")
  if [ -n "$number" ]; then
    gh issue edit "$number" --milestone "$milestone" > /dev/null
    echo "$id (#$number) → $milestone"
  else
    echo "$id açık bir issue olarak bulunamadı; atlandı"
  fi
}

create_issue "İ-32 Kubernetes'in tamamlanması" "chore,altyapi,must" <<'EOF'
## Amaç

Kubernetes dağıtımının üretim standartlarına getirilmesi.

## Gereksinimler

FOG-13, FOG-20, FOG-35, FOG-36, FOG-37

## Bağımlılık

İ-03

## Kabul ölçütleri

- Her bileşen için CPU ve bellek istekleri ve sınırları tanımlı.
- API ve işçide startup, liveness ve readiness kontrolleri; Elasticsearch'te gerçek sağlık kontrolü.
- API birden fazla kopyayla, kesintisiz güncellemeyle çalışıyor.
- Küme dışına açılan adresler yalnızca HTTPS (kendinden imzalı sertifika); HTTP istekleri HTTPS'e yönlendiriliyor; Keycloak ayarları buna göre.
- Yapılandırma ortama göre ayrılıyor (base ve overlay).
- Sonraya bırakılan güvenlik notları ele alındı: API'ye yalnızca Traefik'in ulaşması, Traefik'in yalnızca uygulamanın namespace'ine bakması, `keycloak` veritabanına erişimin kısıtlanması.
EOF

create_issue "İ-33 Gözlemlenebilirlik" "chore,altyapi,must" <<'EOF'
## Amaç

Sistemin durumunun izlenmesi ve sorunlarda uyarı üretilmesi.

## Gereksinimler

FOG-39, FOG-41

## Bağımlılık

İ-32

## Kabul ölçütleri

- Araçlar gerekçesiyle seçildi ve kuruldu.
- API ve işçinin metrikleri toplanıyor.
- Uyarılar: disk doluluğu %80'i aştığında, bir kaynak art arda başarısız olduğunda, hata oranı yükseldiğinde.
- Uyarıların nasıl görüldüğü dokümana yazıldı.
EOF

create_issue "İ-34 Yedekleme ve geri dönüş" "chore,altyapi,must" <<'EOF'
## Amaç

Verilerin düzenli yedeklenmesi ve yedekten geri dönülebilmesi.

## Gereksinimler

FOG-10, FOG-11

## Bağımlılık

İ-32

## Kabul ölçütleri

- PostgreSQL ve Elasticsearch düzenli yedekleniyor (Elasticsearch, haber metinlerinin tek kaydı; ADR-0019). Yöntem gerekçesiyle seçildi.
- Veri kaybı hedefi (RPO) en fazla 24 saat, geri dönüş süresi (RTO) en fazla 2 saat.
- Yedekten geri dönüş denendi ve sonucu raporlandı.
EOF

create_issue "İ-35 Veri büyümesi analizi" "chore,altyapi,must" <<'EOF'
## Amaç

Veri hacminin büyümesine karşı sistemin hazırlanması.

## Gereksinimler

FOG-42, FOG-43

## Bağımlılık

İ-26

## Kabul ölçütleri

- Yıllık veri büyümesi hesaplandı (haber, görsel, audit, toplama kayıtları).
- Saklama süreleri kesinleşti ve bakım işinin ayarlarına işlendi.
- Disk dolmadan önce uyarı veriliyor (İ-33).
- 1 milyon haber ve 10 milyon audit kaydıyla deneme verisi oluşturuldu; deneme verisi gerçek veriden ayrı ve işaretli.
- Audit bölümlerinin 2028 sonrası için yöntemi yazıldı.
EOF

create_issue "İ-36 Uçtan uca, uyumluluk ve erişilebilirlik testleri" "test,frontend,must" <<'EOF'
## Amaç

Sistemin bütününün kullanıcı gözünden sınanması.

## Gereksinimler

FOG-30, FOG-34, FOG-35

## Bağımlılık

Hafta 3

## Kabul ölçütleri

- Ekran akışlarındaki temel senaryolar Playwright ile Chromium, Firefox ve WebKit'te sınanıyor.
- axe-core ile erişilebilirlik denetimi (WCAG 2.2 AA).
- 360 px ve 1920 px genişliklerde ekranlar düzgün.
- Sonuçlar raporlandı.
EOF

create_issue "İ-37 Güvenlik, dayanıklılık ve kurtarma testleri" "test,altyapi,must" <<'EOF'
## Amaç

Sistemin saldırılara, bileşen kesintilerine ve veri kaybına karşı sınanması.

## Gereksinimler

FOG-09, FOG-10

## Bağımlılık

İ-32, İ-34

## Kabul ölçütleri

- OWASP ZAP taraması yapıldı; bulgular değerlendirildi.
- Elasticsearch, MinIO, işçi ve PostgreSQL kesintilerinde davranış gözlendi.
- Yedekten geri dönüş denendi.
- Sonuçlar raporlandı.
EOF

create_issue "İ-38 Performans testleri" "test,altyapi,must" <<'EOF'
## Amaç

Performans hedeflerinin ölçülmesi.

## Gereksinimler

FOG-01, FOG-02, FOG-06, FOG-07

## Bağımlılık

İ-32, İ-33, İ-35

## Kabul ölçütleri

- k6 senaryoları depoda; hedefler eşik olarak senaryonun içinde.
- Yük, stres, ani yük, uzun süre, ölçeklenebilirlik (1 ve 2 kopya) ve hacim testleri çalıştırıldı.
- Raporlar `docs/test-raporlari/` altında; ortamın sınırlamaları belirtildi (R-25).
EOF

create_issue "İ-39 Kullanılabilirlik testi" "test,frontend,must" <<'EOF'
## Amaç

Uygulamanın ilk kez kullananlar için anlaşılır olduğunun sınanması.

## Gereksinimler

Yok (test stratejisi 7.4)

## Bağımlılık

Hafta 3

## Kabul ölçütleri

- En az 3 kişiyle görev temelli test yapıldı.
- SUS anketi uygulandı; hedefler: görevlerin en az %80'i yardımsız tamamlanıyor, SUS puanı en az 68.
- Sonuçlar ve bulgular raporlandı.
EOF

create_issue "İ-40 README, kurulum dokümantasyonu ve OpenAPI belgesi" "docs,backend,must" <<'EOF'
## Amaç

Projenin ilk kez görenler tarafından kurulabilmesi ve API'nin belgelenmesi.

## Gereksinimler

FOG-26, FOG-38

## Bağımlılık

—

## Kabul ölçütleri

- OpenAPI belgesi koddan üretiliyor ve güncel.
- README ve kurulum dokümanı, depoyu ilk kez gören birinin ek bilgiye ihtiyaç duymadan kurabileceği hâlde.
EOF

create_issue "İ-41 Ek Türk haber kaynakları" "feat,backend,must" <<'EOF'
## Amaç

Toplanan haber kaynaklarının 10–15 Türk haber kaynağıyla genişletilmesi.

## Gereksinimler

FG-VT-01, FG-VT-05

## Bağımlılık

İ-22

## Kabul ölçütleri

- Aday kaynakların kullanım şartları, RSS beslemeleri ve robots.txt kuralları araştırıldı; sonuç araştırma dokümanına işlendi.
- Uygun bulunan kaynaklar beslemeleri ve kategori eşlemeleriyle eklendi.
- Yeni kaynaklardan toplama kümede denendi.
EOF

move_issue "İ-13" "$MILESTONE"
for id in İ-28 İ-29 İ-30 İ-31; do
  move_issue "$id" "$LATER"
done
