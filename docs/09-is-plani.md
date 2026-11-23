# İş Planı

## 1. Amaç ve Süre

Bu doküman, uygulamanın geliştirilmesini iş kalemlerine böler, sıralar ve haftalara dağıtır.

- **Süre:** Hafta 1 (2–6 Kasım) analiz ve tasarıma ayrılmıştır. Geliştirme için 3 hafta kalmaktadır: 9 Kasım – 27 Kasım 2026.
- **Takip:** Her haftanın başında o haftanın iş kalemleri GitHub'da issue olarak açılır ve haftanın kilometre taşına bağlanır (ADR-0008). Her issue'da iş kaleminin kimliği ve ilgili gereksinim kimlikleri belirtilir.

## 2. Kurallar

1. **Testler işin içinde yazılır.** Bir iş kalemi, birim, entegrasyon ve gerekiyorsa API testleri yazılmadan bitmiş sayılmaz (`08-test-stratejisi.md`). Hafta 4'teki testler, yalnızca sistemin bütünü çalışınca yapılabilen testlerdir.
2. **İskelet baştan Kubernetes'te kurulur.** Keycloak, JWT doğrulaması ve Kubernetes entegrasyonlarındaki sorunların geç fark edilmesi riskine karşı (R-30), özellik geliştirmeden önce bütün bileşenler yerel Kubernetes'te uçtan uca bağlanır.
3. **Önce Must.** Her haftanın içinde önce Must, sonra Should ve Could işler yapılır.
4. **Geride kalınırsa:** Bir haftanın Çarşamba günü plana göre geride kalındığı görülürse, önce Could, sonra Should iş kalemleri sonraki haftaya veya kapsam dışına alınır. Must iş kalemleri ertelenmez. Plan erken biterse kalan süre Should ve Could işlere ayrılır.
5. **Plan her Cuma gözden geçirilir.** Haftalık ilerleme notu yazılırken plan ve risk kaydı birlikte güncellenir.

## 3. İş Kalemleri

### Hafta 2 (9–13 Kasım): Hazırlık, çalışan iskelet ve toplama

| Kimlik | İş | Gereksinim | Bağımlılık |
|---|---|---|---|
| İ-01 | Kalan kararlar: frontend mimarisi (derleme aracı, durum yönetimi, yönlendirme, çeviri altyapısı), yerel Kubernetes ortamı, MinIO'nun kurulum yöntemi, veritabanı geçiş aracı, modül sınırı denetimi, CI tarama araçları | — | — |
| İ-02 | Kodlama standartları dokümanı: OOP ve clean code ilkeleri, Java ve Python kuralları, stil araçları | FOG-28 | — |
| İ-03 | Yerel Kubernetes ortamı ve altyapı bileşenleri: PostgreSQL (uygulama ve Keycloak veritabanları, veritabanı kullanıcıları), Elasticsearch, MinIO, Keycloak, Mailpit | — | İ-01 |
| İ-04 | Veritabanı geçiş betikleri: bütün tablolar, kısıtlar ve indeksler; audit bölümleri ve tetikleyici; kategoriler, kaynaklar ve beslemelerin başlangıç verisi | FOG-25 | İ-01 |
| İ-05 | Keycloak realm'i: istemciler, kendi kendine kayıt, e-posta doğrulaması (Mailpit), olay kayıtları. Oturum kimliği (`sid`) ve Türkçe dil desteğinin doğrulanması | FG-KY-01 | İ-03 |
| İ-06 | Spring Boot iskeleti: modüller, JWT doğrulaması, kullanıcı eşleştirme ve durum kontrolü, `GET /me`, hata yanıtları, istek kimliği | FG-KY-02–07, FOG-19, FOG-27, FOG-39 | İ-03, İ-04, İ-05 |
| İ-07 | React iskeleti: proje, Keycloak ile giriş (PKCE), token'ın bellekte tutulması, hesap durumu ekranı, çeviri altyapısı | FG-KY-01, FOG-31 | İ-01, İ-05, İ-06 |
| İ-08 | Python işçisi iskeleti: proje (uv), veritabanı bağlantısı, zamanlayıcı döngüsü, sağlık uç noktası, yapılandırma | FOG-13 | İ-03, İ-04 |
| İ-09 | Temel CI: derleme, testler, kapsam, kod stili, commit mesajı denetimi, gizli bilgi ve bağımlılık taraması, yol filtreleri | FOG-17, FOG-18, FOG-23, FOG-24, FOG-28, FOG-29 | İ-06, İ-07, İ-08 |
| İ-10 | RSS ve Atom okuyucuları; alan eşlemesi; normalleştirme (UTC, HTML temizleme, `<img>` çıkarma, adres normalleştirme) | FG-VT-01–03, FG-VT-08, FG-VT-09, FOG-16 | İ-08 |
| İ-11 | Kategori eşlemesi: gerçek beslemelerdeki kategori değerlerinin toplanması, eşleme tablolarının hazırlanması, iki düzeyli eşleme ve "Diğer" kuralı | FG-VT-12, FG-VT-13 | İ-10 |
| İ-12 | Kaydetme ve toplama akışı: tekrar kontrolü, toplama kayıtları, yeniden deneme ve otomatik devre dışı bırakma, ortak istek sınırlayıcısı, koşullu istekler, robots.txt | FG-VT-04–06, FG-VT-10, FG-YP-07 | İ-10 |

### Hafta 3 (16–20 Kasım): Arama, kişisel işlevler ve yönetim

| Kimlik | İş | Gereksinim | Bağımlılık |
|---|---|---|---|
| İ-13 | NYT okuyucusu: bölüm seçimi ve eşleme tablosu, son 24 saatlik istek bütçesi, API anahtarının loglarda maskelenmesi | FG-VT-02, FOG-05 | İ-12 |
| İ-14 | Görsel indirme: kuyruk, içerik doğrulaması, 20 MB sınırı, MinIO'ya yükleme, NYT görsellerinin tek boyutu | FG-VT-14 | İ-12 |
| İ-15 | Elasticsearch: indeks şablonu ve dil analizörleri, yaşam döngüsü politikası, takma ad; outbox aktarımı; tam yeniden indeksleme | — | İ-12 |
| İ-16 | Audit altyapısı: kayıt yazma, yeni oturum kaydı, reddedilen isteklerin kaydı | FG-AL-01–05 | İ-06 |
| İ-17 | Arama API'si: sorgu, filtreler, sıralama, vurgulama, sayfalama ve sınırı, Son Dakika süresi, soğuk haberlerin ağırlığı; kaynak ve kategori listeleri | FG-AR-01–05, FG-AR-11, FG-AR-12 | İ-15 |
| İ-18 | Haber detayı ve imzalı görsel uç noktası | FG-AR-06–08 | İ-14, İ-17 |
| İ-19 | Frontend: arama ve haber detayı ekranları, NYT logosu, arama durumunun adres çubuğunda tutulması | FOG-30, FOG-31, FOG-33, FOG-34 | İ-17, İ-18 |
| İ-20 | Kaydedilen haberler: API ve ekran | FG-KO-01–03 | İ-18 |
| İ-21 | Yönetim: kullanıcılar (onaylama, reddetme, rol ve durum, son aktif yönetici kuralı) | FG-YP-01–03 | İ-16 |
| İ-22 | Yönetim: kaynaklar ve beslemeler, sağlık durumu, elle toplama, toplama geçmişi | FG-YP-04–08 | İ-12, İ-16 |
| İ-23 | Yönetim: audit arama ve CSV dışa aktarma | FG-YP-10, FG-YP-11 | İ-16 |
| İ-24 | Kaynak içeriğinin silinmesi | FG-YP-14 | İ-14, İ-15, İ-22 |
| İ-25 | Yönetim: pano ve istatistikler | FG-YP-12 | İ-22 |
| İ-26 | Yaşam döngüsü işi ve temizlik işleri (işlenmiş outbox kayıtları, toplama kayıtları, besleme testleri) | — | İ-15 |

**Should ve Could iş kalemleri** (Hafta 3'ün sonunda; Must işler bitmemişse Hafta 4'e veya kapsam dışına):

| Kimlik | İş | Gereksinim | Öncelik |
|---|---|---|---|
| İ-27 | Haber gizleme, gizlemenin geri alınması ve gizlenen haberler ekranı | FG-YP-09, FG-AR-09 | Should |
| İ-28 | Kaynaklar arası gruplama ve tek sonuç olarak gösterilmesi | FG-VT-11, FG-AR-10 | Should |
| İ-29 | Besleme testi | FG-YP-13 | Should |
| İ-30 | Kaydedilmiş aramalar | FG-KO-04 | Could |
| İ-31 | İstek sınırı | FOG-21 | Could |

### Hafta 4 (23–27 Kasım): Üretim standartları ve testler

| Kimlik | İş | Gereksinim | Bağımlılık |
|---|---|---|---|
| İ-32 | Kubernetes'in tamamlanması: kaynak sınırları, probe'lar, kesintisiz güncelleme, Secret'lar, ortama göre yapılandırma, HTTPS | FOG-13, FOG-36, FOG-37 | İ-03 |
| İ-33 | Gözlemlenebilirlik: araçların seçimi; yapılandırılmış loglar, metrikler, uyarılar (disk %80, kaynak hataları, hata oranı) | FOG-39, FOG-41 | İ-32 |
| İ-34 | Yedekleme ve geri dönüş: yöntemin seçimi ve uygulanması | FOG-10, FOG-11 | İ-32 |
| İ-35 | Veri büyümesi analizi: yıllık büyüme hesabı, saklama süreleri, arşivleme veya silme, disk dolmadan önce uyarı; büyük hacimli deneme verisiyle doğrulama | FOG-42, FOG-43 | İ-26 |
| İ-36 | Uçtan uca, uyumluluk ve erişilebilirlik testleri | FOG-30, FOG-34, FOG-35 | Hafta 3 |
| İ-37 | Güvenlik, dayanıklılık ve kurtarma testleri | FOG-09, FOG-10 | İ-32, İ-34 |
| İ-38 | Performans testleri (yük, stres, ani yük, uzun süre, ölçeklenebilirlik, hacim) ve raporları | FOG-01, FOG-02, FOG-06, FOG-07 | İ-32, İ-33, İ-35 |
| İ-39 | Kullanılabilirlik testi (en az 3 kişi, SUS anketi) | — | Hafta 3 |
| İ-40 | README, kurulum dokümantasyonu ve OpenAPI belgesi | FOG-26, FOG-38 | — |
| İ-13 | NYT okuyucusu (Hafta 3'ten taşındı) | FG-VT-02, FOG-05 | İ-12 |
| İ-41 | Ek Türk haber kaynakları (10–15): kullanım şartlarının ve robots.txt'nin araştırılması, kaynak ve beslemelerin eklenmesi, kategori eşlemeleri | FG-VT-01, FG-VT-05 | İ-22 |

**Planlanan sıra (22 Kasım):**

| Gün | İş kalemleri |
|---|---|
| Pazartesi 23 | İ-32 (HTTPS kendinden imzalı sertifikayla) |
| Salı 24 | İ-33, İ-34 |
| Çarşamba 25 | İ-35, İ-38 (uzun süre testi arka planda, Perşembe'ye taşabilir); akşam durum değerlendirmesi (kural 4) |
| Perşembe 26 | İ-36, İ-37, İ-40 |
| Cuma 27 (sabah) | İ-13, İ-41; Hafta 4 ilerleme notu |

Geride kalınırsa Must iş kalemleri ertelenmez; kapsamları daraltılır (örneğin uyarılarda yalnızca FOG-41'in saydıkları, performans testlerinde öncelikle yük, hacim ve ölçeklenebilirlik). İ-41'deki kaynakların araştırması uzun sürebileceğinden aday kaynaklara hafta içinde bakılmaya başlanır.

**Her Cuma:** Haftalık ilerleme notu, planın ve risk kaydının gözden geçirilmesi.

## 4. Kritik Yol ve Riskler

- **Kritik yol:** İskelet (İ-03 → İ-06 → İ-08) → toplama (İ-10 → İ-12) → Elasticsearch (İ-15) → arama (İ-17). Bu zincirdeki bir gecikme, arama ve yönetim işlevlerini doğrudan geciktirir.
- **En yoğun hafta Hafta 4'tür.** Uzun süre testi tek başına 4 saat sürer ve performans testleri ancak sistemin geri kalanı hazır olduğunda yapılabilir. Bu yüzden Hafta 3'ün sonunda bütün Must iş kalemlerinin bitmiş olması gerekir.
- **Uzun süren testler çalışma saatlerine yayılır:** Uzun süre testi, başka işler yapılırken arka planda çalıştırılır.
- Planla ilgili risk R-28'dir (kullanılan teknolojilerle ilk kez çalışılması nedeniyle gecikme).