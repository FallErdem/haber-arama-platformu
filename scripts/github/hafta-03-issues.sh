#!/usr/bin/env bash
# Hafta 3 iş kalemlerini (docs/09-is-plani.md, İ-13 – İ-31) GitHub issue olarak açar.
# "Hafta 3" kilometre taşı yoksa önce onu oluşturur.
set -euo pipefail

MILESTONE="Hafta 3"
MILESTONE_DUE="2026-11-20T00:00:00Z"

# Kilometre taşı varsa yeniden oluşturulmaz; betik bu adımda hata vermeden devam eder.
if ! gh api "repos/{owner}/{repo}/milestones?state=all" --jq '.[].title' | grep -qx "$MILESTONE"; then
  gh api "repos/{owner}/{repo}/milestones" -f title="$MILESTONE" -f due_on="$MILESTONE_DUE" --silent
  echo "Kilometre taşı oluşturuldu: $MILESTONE"
fi

create_issue() {
  local title="$1"
  local labels="$2"
  gh issue create --title "$title" --label "$labels" --milestone "$MILESTONE" --body-file -
}

create_issue "İ-13 NYT okuyucusu" "feat,backend,must" <<'EOF'
## Amaç

New York Times Top Stories API'sinden haber toplanması.

## Gereksinimler

FG-VT-02, FOG-05

## Bağımlılık

İ-12

## Kabul ölçütleri

- NYT kaynağı, seçilen bölümleri ve bölüm → kategori eşleme tablosu geçiş betiğiyle eklendi.
- Okuyucu API yanıtını ortak yapıya (`ParsedArticle`) çeviriyor.
- Son 24 saatteki istek sayısı izleniyor; zamanlanmış toplama günlük limitin en fazla %80'ini kullanıyor.
- API anahtarı Secret'tan okunuyor; loglarda ve hata metinlerinde maskeleniyor.
- Testler yazıldı.
EOF

create_issue "İ-14 Görsel indirme" "feat,backend,must" <<'EOF'
## Amaç

Haber görsellerinin kaynaktan indirilip nesne depolamada saklanması.

## Gereksinimler

FG-VT-14

## Bağımlılık

İ-12

## Kabul ölçütleri

- `media` tablosundaki bekleyen kayıtlar kuyruk olarak işleniyor; başarısız indirmeler yeniden deneniyor, belirli sayıda denemeden sonra `FAILED` oluyor.
- İndirilen dosyanın gerçekten bir görsel olduğu doğrulanıyor; 20 MB'tan büyük dosyalar alınmıyor.
- Görsel MinIO'ya `articles/{article_id}/{media_id}` anahtarıyla yükleniyor; tür, boyut, genişlik ve yükseklik kaydediliyor.
- Görsel indirmeleri, besleme okumalarıyla aynı kaynak başına istek sınırlayıcısını kullanıyor.
- Adresinde ASCII dışı karakter bulunan görseller indirilebiliyor.
- NYT görsellerinden tek boyut indiriliyor.
- Testler yazıldı.
EOF

create_issue "İ-15 Elasticsearch ve outbox aktarımı" "feat,backend,must" <<'EOF'
## Amaç

Haberlerin Elasticsearch'e aktarılması ve arama indeksinin kurulması.

## Bağımlılık

İ-12

## Kabul ölçütleri

- İndeks şablonu, Türkçe ve İngilizce dil analizörleri, yaşam döngüsü politikası ve `articles` takma adı oluşturuldu.
- Outbox aktarımı çalışıyor: bekleyen kayıtlar sırayla işleniyor, başarısız olanlar yeniden deneniyor, aynı kaydın iki kez işlenmesi sonucu değiştirmiyor.
- Elasticsearch erişilemezken kayıtlar birikiyor, erişilebilir olduğunda aktarılıyor.
- Tam yeniden indeksleme işi çalışıyor.
- Türkçe analizör gerçek haberlerle denendi.
- Testler yazıldı.
EOF

create_issue "İ-16 Audit altyapısı" "feat,backend,must" <<'EOF'
## Amaç

API'de audit kayıtlarının yazılması.

## Gereksinimler

FG-AL-01 – FG-AL-05

## Bağımlılık

İ-06

## Kabul ölçütleri

- Audit kaydı, ilgili işlemle aynı veritabanı işleminde yazılıyor.
- Yeni oturum kaydı (`sid` değiştiğinde) ve kullanıcı kaydının oluşturulması kaydediliyor.
- Kimliği doğrulanmış kullanıcıların reddedilen istekleri (403) kaydediliyor.
- Kayıtlarda parola, token veya API anahtarı bulunmadığı testlerle doğrulandı.
- Testler yazıldı.
EOF

create_issue "İ-17 Arama API'si" "feat,backend,must" <<'EOF'
## Amaç

Haberlerde arama yapılmasını sağlayan API.

## Gereksinimler

FG-AR-01 – FG-AR-05, FG-AR-11, FG-AR-12

## Bağımlılık

İ-15

## Kabul ölçütleri

- Anahtar kelimeyle arama başlık, özet ve tam metin üzerinde çalışıyor; başlıktaki eşleşme en yüksek ağırlığı alıyor.
- Kaynak, tarih aralığı, dil ve kategori filtreleri çalışıyor.
- İlgililiğe ve tarihe göre sıralama, vurgulama ve sayfalama (üst sınırıyla birlikte) çalışıyor.
- Son Dakika kategorisi yalnızca yapılandırılan süre içindeki haberleri gösteriyor.
- Soğuk haberler sıralamada geriye düşüyor.
- Gizlenen haberler sonuçlarda görünmüyor.
- Kaynak ve kategori listeleri uç noktaları çalışıyor.
- Testler yazıldı.
EOF

create_issue "İ-18 Haber detayı ve imzalı görsel uç noktası" "feat,backend,must" <<'EOF'
## Amaç

Haber detayının ve görsellerin API üzerinden sunulması.

## Gereksinimler

FG-AR-06 – FG-AR-08

## Bağımlılık

İ-14, İ-17

## Kabul ölçütleri

- Haber detayı başlık, tam metin veya özet, yayın tarihi, kaynak, yazar, medya, özgün bağlantı ve atıf bilgisiyle dönüyor.
- Görseller MinIO'dan, HMAC imzalı ve süreli adreslerle API üzerinden sunuluyor; imzası geçersiz veya süresi dolmuş adres reddediliyor.
- Görseli olmayan veya indirilemeyen haberlerde yer tutucu bilgisi dönüyor.
- Testler yazıldı.
EOF

create_issue "İ-19 Frontend: arama ve haber detayı ekranları" "feat,frontend,must" <<'EOF'
## Amaç

Kullanıcının haber arayıp okuyabildiği ekranlar.

## Gereksinimler

FOG-30, FOG-31, FOG-33, FOG-34

## Bağımlılık

İ-17, İ-18

## Kabul ölçütleri

- Arama ekranı: arama kutusu, filtreler, sıralama, vurgulama ve sayfalama çalışıyor.
- Arama durumu adres çubuğunda tutuluyor; adres paylaşıldığında aynı sonuç açılıyor.
- Haber detayı ekranı kaynak adını, özgün bağlantıyı ve atfı gösteriyor; NYT haberlerinde NYT logosu yer alıyor.
- Metinler dil dosyalarından okunuyor.
- Ekranlar 360 px ile 1920 px arasında kullanılabiliyor ve klavyeyle gezilebiliyor.
- Testler yazıldı.
EOF

create_issue "İ-20 Kaydedilen haberler" "feat,backend,must" <<'EOF'
## Amaç

Kullanıcının haber kaydedip kaydettiklerini listeleyebilmesi (API ve ekran).

## Gereksinimler

FG-KO-01 – FG-KO-03

## Bağımlılık

İ-18

## Kabul ölçütleri

- Kullanıcı bir haberi kaydedebiliyor ve listeden çıkarabiliyor.
- Kaydedilen haberler sayfalı listeleniyor.
- Gizlenen bir haber listede "gizlendi" olarak gösteriliyor.
- Bir kullanıcı başka bir kullanıcının kayıtlarını göremiyor.
- Testler yazıldı.
EOF

create_issue "İ-21 Yönetim: kullanıcılar" "feat,backend,must" <<'EOF'
## Amaç

Yöneticinin kullanıcıları yönetebilmesi (API ve ekran).

## Gereksinimler

FG-YP-01 – FG-YP-03

## Bağımlılık

İ-16

## Kabul ölçütleri

- Kullanıcılar listelenebiliyor ve aranabiliyor.
- Onay bekleyen kullanıcı onaylanabiliyor veya reddedilebiliyor.
- Kullanıcı pasif veya aktif hale getirilebiliyor; rolü değiştirilebiliyor.
- Son aktif yönetici pasif hale getirilemiyor ve rolü düşürülemiyor.
- Her işlem audit log'a yazılıyor.
- Testler yazıldı.
EOF

create_issue "İ-22 Yönetim: kaynaklar ve beslemeler" "feat,backend,must" <<'EOF'
## Amaç

Yöneticinin kaynakları, beslemeleri ve toplama durumunu yönetebilmesi (API ve ekran).

## Gereksinimler

FG-YP-04 – FG-YP-08

## Bağımlılık

İ-12, İ-16

## Kabul ölçütleri

- Kaynak ve besleme eklenebiliyor, düzenlenebiliyor ve devre dışı bırakılabiliyor.
- Her kaynağın ve beslemenin sağlık durumu (son başarılı toplama, art arda hata sayısı, otomatik devre dışı kalma) gösteriliyor.
- Toplama geçmişi görüntülenebiliyor.
- Elle toplama başlatılabiliyor; elle başlatılan okuma `ingestion_runs.trigger` alanında `MANUAL` olarak kaydediliyor (İ-12'de ertelendi).
- Her işlem audit log'a yazılıyor.
- Testler yazıldı.
EOF

create_issue "İ-23 Yönetim: audit arama ve CSV dışa aktarma" "feat,backend,must" <<'EOF'
## Amaç

Yöneticinin audit kayıtlarını inceleyebilmesi (API ve ekran).

## Gereksinimler

FG-YP-10, FG-YP-11

## Bağımlılık

İ-16

## Kabul ölçütleri

- Audit kayıtları görüntülenebiliyor, aranabiliyor ve filtrelenebiliyor.
- Filtrelenmiş kayıtlar CSV olarak dışa aktarılabiliyor.
- Testler yazıldı.
EOF

create_issue "İ-24 Kaynak içeriğinin silinmesi" "feat,backend,must" <<'EOF'
## Amaç

Bir kaynağın bütün içeriğinin (haberler ve görseller) silinebilmesi.

## Gereksinimler

FG-YP-14

## Bağımlılık

İ-14, İ-15, İ-22

## Kabul ölçütleri

- Yönetici silmeyi istiyor (`sources.purge_requested_at`); işçi silmeyi yürütüyor.
- Önce MinIO'daki dosyalar, ardından veritabanı kayıtları siliniyor; Elasticsearch için `DELETE` outbox kayıtları aynı işlemde yazılıyor.
- İşlem audit log'a yazılıyor.
- Testler yazıldı.
EOF

create_issue "İ-25 Yönetim: pano ve istatistikler" "feat,backend,must" <<'EOF'
## Amaç

Yönetim panelinde sistemin durumunun ve temel istatistiklerin gösterilmesi (API ve ekran).

## Gereksinimler

FG-YP-12

## Bağımlılık

İ-22

## Kabul ölçütleri

- Sistem bileşenlerinin durumu gösteriliyor.
- Toplam ve kaynak bazında haber sayısı, son 24 saatte toplanan haber sayısı ve kullanıcı sayısı gösteriliyor.
- Testler yazıldı.
EOF

create_issue "İ-26 Yaşam döngüsü işi ve temizlik işleri" "feat,backend,must" <<'EOF'
## Amaç

Haberlerin yaşam döngüsü durumunun güncellenmesi ve eski yardımcı kayıtların temizlenmesi.

## Bağımlılık

İ-15

## Kabul ölçütleri

- Haberlerin durumu yaşına göre güncelleniyor (30 güne kadar HOT, 1 yıla kadar WARM, daha eskisi COLD).
- İşlenmiş outbox kayıtları, eski toplama kayıtları ve besleme testleri saklama sürelerine göre siliniyor.
- Testler yazıldı.
EOF

create_issue "İ-27 Haber gizleme" "feat,backend,should" <<'EOF'
## Amaç

Yöneticinin bir haberi gizleyebilmesi ve gizlemeyi geri alabilmesi (API ve ekran).

## Gereksinimler

FG-YP-09, FG-AR-09

## Kabul ölçütleri

- Haber gerekçe belirtilerek gizlenebiliyor; gizleme geri alınabiliyor.
- Gizlenen haber aramada ve haber detayında görünmüyor; değişiklik outbox üzerinden Elasticsearch'e yansıyor.
- Gizlenen haberler ekranı çalışıyor.
- Her işlem audit log'a yazılıyor.
- Testler yazıldı.
EOF

create_issue "İ-28 Kaynaklar arası gruplama" "feat,backend,should" <<'EOF'
## Amaç

Farklı kaynaklarda yayımlanan aynı haberin gruplanması ve tek sonuç olarak gösterilmesi.

## Gereksinimler

FG-VT-11, FG-AR-10

## Kabul ölçütleri

- Gruplama yöntemi belirlendi ve gerekçesiyle dokümana yazıldı.
- Yalnızca çok benzer haberler gruplanıyor; asıl haber kayıtları değişmiyor.
- Gruplanmış haberler aramada tek sonuç olarak gösteriliyor; diğer kaynaklar bağlantılarıyla listeleniyor.
- Testler yazıldı.
EOF

create_issue "İ-29 Besleme testi" "feat,backend,should" <<'EOF'
## Amaç

Kaynak veya besleme eklenirken bağlantının test edilebilmesi.

## Gereksinimler

FG-YP-13

## Kabul ölçütleri

- Yönetici bir besleme adresi için test isteyebiliyor (`feed_tests`); işçi testi yürütüp sonucu yazıyor.
- Alan eşlemesinin sonucu örnek bir haber üzerinde önizlenebiliyor.
- Testler yazıldı.
EOF

create_issue "İ-30 Kaydedilmiş aramalar" "feat,backend,could" <<'EOF'
## Amaç

Kullanıcının bir aramayı filtreleriyle birlikte kaydedip yeniden çalıştırabilmesi.

## Gereksinimler

FG-KO-04

## Kabul ölçütleri

- Arama bir adla kaydedilebiliyor ve tek adımda yeniden çalıştırılabiliyor.
- Testler yazıldı.
EOF

create_issue "İ-31 İstek sınırı" "feat,backend,could" <<'EOF'
## Amaç

API'ye yapılan isteklerin sınırlandırılması.

## Gereksinimler

FOG-21

## Kabul ölçütleri

- Kullanıcı başına istek hızı sınırı uygulanıyor (varsayılan: dakikada 120 istek).
- Sınır aşıldığında API 429 dönüyor.
- Testler yazıldı.
EOF

echo "Hafta 3 issue'ları oluşturuldu."
