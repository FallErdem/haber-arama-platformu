# Test Stratejisi

## 1. Amaç

Bu doküman, uygulamanın hangi testlerle, hangi araçlarla, hangi ortamda ve hangi hedeflere göre test edileceğini tanımlar. Şartnamenin istediği bütün test türleri kapsanır; hedef değerler testler çalıştırılmadan önce burada yazılır.

## 2. İlkeler

- **Test piramidi:** Birim testleri sayıca en çok, hızlı ve ucuzdur; entegrasyon testleri daha az, uçtan uca testler en azdır. Bir hata en alttaki uygun düzeyde yakalanır. Uçtan uca testler yalnızca kullanıcı senaryolarının bütün olarak çalıştığını doğrular.
- **Gerçek bağımlılıklar:** Entegrasyon testleri sahte veritabanları yerine gerçek PostgreSQL, Elasticsearch ve MinIO ile çalışır. Sahte bir veritabanıyla geçen ama gerçekte bozulan testler bu şekilde önlenir.
- **Her değişiklikte:** Otomatikleştirilebilen bütün testler her PR'da ve `main`'e yapılan her gönderimde CI'da çalışır (ADR-0008). Performans, güvenlik taraması, dayanıklılık, kurtarma ve kullanılabilirlik testleri uzun sürdükleri veya insan gözlemi gerektirdikleri için elle ve her kilometre taşında çalıştırılır.
- **Hata önce testle:** Bir hata düzeltilmeden önce o hatayı yeniden üreten bir test yazılır. Böylece hata bir daha aynı şekilde geri gelemez.
- **Sonuç kötü çıkarsa:** Amaç iyi bir sayı göstermek değil; kötü sonucun nedeni bulunur, düzeltilir ve rapora yazılır.

## 3. Ortamlar

| Ortam | Kullanım | Not |
|---|---|---|
| Geliştirme bilgisayarı | Testlerin yazılması ve elle çalıştırılması | 16 çekirdek, 32 GB RAM |
| CI (GitHub Actions) | Otomatik testler | Testcontainers'ın ihtiyaç duyduğu Docker, GitHub'ın Linux sunucularında bulunur |
| Yerel Kubernetes | Performans, dayanıklılık ve kurtarma testleri | Bileşenler kaynak sınırlarıyla çalışır (FOG-36) |

Performans testlerinde yük üreten araç ve test edilen sistem aynı bilgisayarda çalışır. Bu sınırlama her raporda belirtilir; yük aracı ile sistem kaynak sınırlarıyla ayrılır ve sonuçlar mutlak değerlerden çok karşılaştırmalı yorumlanır (R-25).

## 4. Test Verisi

- **Birim ve entegrasyon testleri:** Her test kendi verisini hazırlar ve başka testlerin verisine bağlı değildir. Beslemeler için kaynaklardan alınmış gerçek örnek RSS, Atom ve NYT yanıtları test dosyası olarak saklanır; bunlara bozuk ve zararlı içerikli örnekler eklenir.
- **Kullanıcılar ve token'lar:** API testlerinde token'lar testin kendi anahtarıyla üretilir ve doğrulama bu anahtarın açık eşiyle yapılır; böylece testler Keycloak'a bağımlı olmadan hızlı çalışır. Uçtan uca testlerde gerçek Keycloak ve Mailpit kullanılır.
- **Hacim testi:** 1 milyon haber ve 10 milyon audit kaydı üretilir (`deploy/README.md`, 14. adım). Haberlerin metinleri gerçek haberlerin kelime dağılımına ve uzunluklarına göre üretilir ve gerçek toplama yolundan kaydedilir. Deneme verisi gerçek veriden ayrı tutulur ve işaretlenir (R-26): haberler kapalı `DENEME` kaynağına, audit kayıtları Kasım 2026 öncesine ait geçici bölümlere yazılır; iş bitince silinir. NYT Archive API kullanılmaz: haberleri yalnızca İngilizce ve tam metinsizdir, NYT içeriği gösteren her ekranda NYT logosu da zorunludur.

## 5. Fonksiyonel Testler

### 5.1 Birim testleri

**Soru:** Tek bir parça doğru çalışıyor mu?

| Bileşen | Araç | Kapsam hedefi |
|---|---|---|
| Spring Boot API | JUnit 5, Mockito, AssertJ; kapsam ölçümü JaCoCo | İş mantığında en az %80 satır kapsamı (FOG-23) |
| Python işçisi | pytest, pytest-asyncio, respx; kapsam ölçümü pytest-cov | İş mantığında en az %80 satır kapsamı (FOG-23) |
| Frontend | Vitest, React Testing Library | Hedef yok; bileşenlerin davranışı test edilir |
| Uyarı kuralları (Prometheus) | promtool | Her kural için uyarının çıktığı ve çıkmadığı durumlar |

Örnekler: Türkçe küçük harf dönüşümü ("İSTANBUL", "IĞDIR"), adres normalleştirme, kategori eşlemesi ve "Diğer" kuralı, tarih dönüşümleri, imzalı görsel adresinin üretilmesi ve doğrulanması, CSV enjeksiyonuna karşı önlem.

**Neden bu araçlar:**
- **JUnit 5, Mockito, AssertJ:** Spring Boot'un test altyapısı bunlar üzerine kurulu. Alternatif TestNG, Spring ile daha az kullanılıyor ve ek bir fayda sağlamıyor.
- **respx:** httpx isteklerini taklit eder; okuyucular internete çıkmadan, kaydedilmiş besleme örnekleriyle test edilir. Alternatifi gerçek kaynaklara istek atmak: Testler kaynakların o anki durumuna bağlı olur ve kaynaklara gereksiz yük bindirir.
- **Vitest:** Frontend'in derleme aracı Vite'tır (ADR-0018); Vitest aynı yapılandırmayı kullanır. Alternatif Jest, Vite ile ayrıca yapılandırma gerektirir.
- **React Testing Library:** Bileşenleri kullanıcının gördüğü gibi (metin, düğme, etiket) test eder; bileşenin iç yapısına bağlı testler yazılmasını engeller.
- **promtool:** Prometheus'un kendi aracıdır. Kuralları sahte ölçümlerle ve zamanı ileri sararak dener; bir uyarının çıktığını görmek için kümede dakikalarca beklemek veya gerçek bir arıza çıkarmak gerekmez.

### 5.2 Entegrasyon testleri

**Soru:** Parçalar ve veritabanları birlikte çalışıyor mu?

- **Araç:** Testcontainers (Java ve Python). Test sırasında gerçek PostgreSQL, Elasticsearch ve MinIO konteynerleri başlatılır, veritabanı geçiş betikleri çalıştırılır ve test bitince konteynerler kaldırılır.
- **Örnekler:**
  - Repository sınıflarının her sorgusu gerçek PostgreSQL'e karşı.
  - Tekrar kontrolü: Aynı haber ikinci kez eklenmez (`ON CONFLICT`).
  - Outbox: Haber kaydı ile outbox kaydının birlikte yazılması; Elasticsearch'e aktarım; Elasticsearch kapalıyken kayıtların birikmesi.
  - Görsel indirme: MinIO'ya yazma ve doğru anahtarla okuma.
  - Audit tablosunda güncelleme ve silmenin reddedilmesi.
  - Ortak yapıların iki uygulamada aynı yorumlanması: İşçinin yazdığı haber ve arama belgesinin API tarafından doğru okunması (R-36).
- **Alternatifler:** Bellekte çalışan veritabanları (H2 gibi) daha hızlıdır ama PostgreSQL'in davranışını birebir taşımaz; `ON CONFLICT`, `jsonb`, bölümleme ve tetikleyiciler gibi kullandığımız özellikler bu yüzden test edilemez. Paylaşılan tek bir test veritabanı ise testlerin birbirini etkilemesine yol açar.

### 5.3 API testleri

**Soru:** Uç noktalar sözleşmeye ve yetki kurallarına uyuyor mu?

- **Araç:** Spring'in test araçları (MockMvc) ve Testcontainers ile gerçek veritabanı.
- **Sözleşme:** Her uç noktanın yanıtının `06-api-sozlesmesi.md`'deki yapıya, durum kodlarına ve hata kodlarına uyduğu.
- **Yetki matrisi:** Her uç nokta, her kullanıcı türüyle denenir ve beklenen sonuç doğrulanır:

| İstek yapan | Beklenen |
|---|---|
| Token yok veya geçersiz | `401 UNAUTHENTICATED` |
| `PENDING` kullanıcı | `403 USER_PENDING_APPROVAL` (`/me` hariç) |
| `PASSIVE` kullanıcı, geçerli token'la | `403 USER_PASSIVE` |
| `REJECTED` kullanıcı | `403 USER_REJECTED` |
| `USER` rolü, yönetim uç noktasına | `403 FORBIDDEN` |
| `ADMIN` rolü | İzin verilir |

- **Diğer örnekler:** Başka bir kullanıcının kaydedilmiş aramasına erişimin `404` dönmesi; iyimser kilitlemede `409 VERSION_CONFLICT`; son aktif yöneticinin kaldırılamaması; kaynak etkinken içerik silmenin reddedilmesi; arama sayfa sınırı.
- **Neden MockMvc:** Testler sunucuyu ağ üzerinden başlatmadan, Spring'in güvenlik katmanı dahil bütün istek işleme zinciriyle çalışır; hızlıdır. Alternatif REST Assured gerçek bir HTTP sunucusu gerektirir; bu testlerde ek bir fayda sağlamaz.

### 5.4 Uçtan uca testler

**Soru:** Kullanıcı senaryosu arayüzden baştan sona çalışıyor mu?

- **Araç:** Playwright.
- **Ortam:** Bütün bileşenler birlikte çalışır: frontend, API, işçi, gerçek Keycloak, Mailpit ve veri depoları. Haber kaynakları yerine kaydedilmiş besleme örneklerini sunan bir test sunucusu kullanılır.
- **Senaryolar** (`07-ekran-akislari.md`, 4. bölüm):
  1. Yeni kullanıcının kaydolması ve yönetici tarafından onaylanması
  2. Arama, filtreleme ve haber kaydetme
  3. Yöneticinin kaynak ve besleme eklemesi, beslemeyi denemesi
  4. Haber gizleme ve gizlemeyi geri alma
  5. Kaynak içeriğinin silinmesi
  6. Kullanıcının pasif yapılması ve erişiminin kesilmesi
- **Neden Playwright:** Chromium, Firefox ve WebKit motorlarında aynı testi çalıştırır; bu sayede uyumluluk testinin büyük kısmı da karşılanır (bkz. 7.5). Sayfa öğelerinin hazır olmasını kendisi bekler, bu da zamanlamaya bağlı rastgele başarısız olan testleri azaltır. Alternatifler: Cypress, Firefox ve WebKit desteği daha sınırlı ve tek bir sekmede çalışıyor; Selenium daha eski ve daha fazla elle bekleme kodu gerektiriyor.

### 5.5 Regresyon testleri

**Soru:** Yeni değişiklik eski bir özelliği bozdu mu?

Ayrı bir araç yoktur. Birim, entegrasyon, API ve uçtan uca testlerin tamamı her PR'da CI'da çalışır; herhangi biri başarısız olursa PR birleştirilmez. Düzeltilen her hata için o hatayı yeniden üreten bir test eklenir.

## 6. Performans Testleri

### 6.1 Araç: k6

- **Neden k6:** Senaryolar JavaScript ile, kod olarak yazılır ve depoda saklanır. Hedefler senaryonun içine eşik (threshold) olarak yazılır: Örneğin "p95 ≤ 500 ms" eşiği aşılırsa test başarısız olur. Bu, şartnamenin "hedefler test öncesinde yazılır" isteğini doğrudan karşılar. Yük üreten aracın kendisi az kaynak tüketir; yük aracı ile sistemin aynı bilgisayarda çalıştığı ortamımızda bu önemlidir (R-25).
- **Alternatifler:**
  - **Gatling:** Senaryolar Java veya Scala ile yazılır, raporları güçlüdür; ancak JVM üzerinde çalıştığından yük aracının kendisi daha fazla kaynak tüketir.
  - **JMeter:** Arayüzlüdür; senaryolar XML dosyaları olarak saklandığından Git'te okunması ve incelenmesi zordur.
  - **Locust:** Senaryolar Python ile yazılır; eşik tanımlama ve sonucu başarılı veya başarısız sayma yeteneği k6'ya göre daha sınırlıdır.

### 6.2 Kullanıcı senaryosu

Bütün performans testleri aynı kullanıcı davranışını kullanır; yalnızca kullanıcı sayısı ve süre değişir:

| İşlem | Pay |
|---|---|
| Arama (filtreli ve filtresiz) | %70 |
| Haber detayı | %20 |
| Haber kaydetme ve kaydedilenler | %10 |

Her işlem arasında 3–5 saniyelik düşünme süresi bulunur. Görsel istekleri de senaryoya dahildir.

### 6.3 Testler ve hedefler

| Test | Soru | Senaryo | Hedef |
|---|---|---|---|
| Yük | Beklenen kullanıcı sayısında sistem nasıl davranıyor? | 50 eş zamanlı kullanıcı, 15 dakika | Arama p95 ≤ 500 ms, p99 ≤ 1000 ms; hata oranı < %1 (FOG-01, FOG-02) |
| Stres | Sistem nerede kırılıyor, kırılınca nasıl davranıyor? | 50 kullanıcıdan başlayıp her 2 dakikada 25 kullanıcı artırılır; hata oranı %5'i veya p95 2 saniyeyi aşınca durdurulur | Hedef değil, gözlem: kırılma noktası kaydedilir. Kırıldığında sistemin çökmemesi, anlamlı hata yanıtları vermesi ve yük düşünce kendiliğinden toparlanması beklenir |
| Ani yük | Trafik birden artınca ne oluyor? | 50 kullanıcıdan 10 saniyede 200 kullanıcıya, 2 dakika sürer, sonra 50'ye döner | Ani yük sırasında hata oranı < %5; yük düştükten sonra 1 dakika içinde yük testi hedeflerine dönülür |
| Uzun süre | Saatler süren yükte bellek veya bağlantı sızıntısı var mı? | 50 kullanıcı, 4 saat (test 2 saat çalıştırıldı; gerekçesi performans raporunda) | Son saatte bellek kullanımı ve veritabanı bağlantı sayısı ilk saate göre %10'dan fazla artmaz; hata oranı < %1 |
| Ölçeklenebilirlik | Kopya sayısı arttıkça kapasite artıyor mu? | Aynı senaryo, API'nin 1 ve 2 kopyasıyla; her durumda yük hedeflerini sağlayan en yüksek istek hızı bulunur | 2 kopyada kapasite, 1 kopyaya göre en az %70 fazla (FOG-06) |
| Hacim | Büyük veri miktarında sorgular yeterince hızlı mı? | 1 milyon haber, yük testi senaryosu | Arama p95 ≤ 500 ms (FOG-07) |

### 6.4 Raporlama

Her performans testi için `docs/test-raporlari/` altında bir rapor yazılır:

| Başlık | İçerik |
|---|---|
| Ortam | Bilgisayar, bileşenlerin sürümleri, kaynak sınırları, kopya sayıları, veri hacmi |
| Senaryo | k6 senaryosu ve parametreleri |
| Hedef | Bu dokümandaki hedef |
| Sonuç | Ölçülen değerler ve hedefle karşılaştırma |
| Darboğaz | Yavaşlığın veya hatanın nedeni ve nasıl bulunduğu |
| İyileştirme | Yapılan değişiklik ve sonrasındaki ölçüm |

## 7. Fonksiyonel Olmayan Testler

### 7.1 Güvenlik

**Soru:** Yaygın açıklar ve yetki atlama denemeleri engelleniyor mu?

| Kontrol | Araç | Ne zaman |
|---|---|---|
| Yetki atlama | API testlerindeki yetki matrisi (5.3) | Her PR |
| Zararlı HTML (XSS) | Zararlı içerikli örnek beslemelerle entegrasyon ve uçtan uca testleri | Her PR |
| Yaygın web açıkları ve eksik güvenlik başlıkları | OWASP ZAP, çalışan uygulamaya karşı | Her kilometre taşında |
| Gizli bilgi ve bağımlılık açıkları | CI'daki taramalar: gitleaks ve Trivy (FOG-17, FOG-18, ADR-0018) | Her PR |

- **Neden OWASP ZAP:** Açık kaynaklı, OWASP'ın kendi projesi; çalışan uygulamaya gerçek saldırı istekleri göndererek kodu incelemeden açık arar. Alternatif Burp Suite'in otomatik tarama özelliği ücretli sürümde.

### 7.2 Dayanıklılık

**Soru:** Bir servis veya veritabanı düşünce sistem ne yapıyor?

Bileşenler yerel Kubernetes'te tek tek durdurulur (`kubectl`) ve beklenen davranış doğrulanır:

| Durdurulan | Beklenen davranış |
|---|---|
| Bir API kopyası | Diğer kopya istekleri karşılamaya devam eder; Kubernetes kopyayı yeniden başlatır |
| Python işçisi | Arama çalışmaya devam eder; yeni haber gelmez; pano uyarı gösterir; işçi yeniden başlayınca zamanı geçmiş beslemeler okunur |
| Elasticsearch | Arama anlamlı bir hata döner; diğer işlevler çalışır (FOG-09); değişiklikler outbox'ta birikir ve Elasticsearch geri gelince aktarılır |
| MinIO | Haberler görselsiz, yer tutucuyla gösterilir; görsel indirmeleri sonra yeniden denenir |
| Keycloak | Geçerli token'ı olan kullanıcılar token süresi dolana kadar çalışmaya devam eder; yeni girişler yapılamaz |
| PostgreSQL | API istekleri anlamlı bir hata döner; PostgreSQL geri geldiğinde uygulamalar yeniden başlatılmadan çalışmaya devam eder |
| Bir haber kaynağı (hata döndüren test sunucusu) | Diğer kaynaklar etkilenmez; besleme art arda 5 hatada otomatik devre dışı kalır |

- **Neden elle senaryolar:** Chaos Mesh gibi kaos mühendisliği araçları rastgele ve sürekli hata enjekte etmek için tasarlanmıştır; bu ölçekte bileşenlerin tek tek ve gözlemlenerek durdurulması yeterlidir ve her senaryonun sonucu ayrı ayrı açıklanabilir.

### 7.3 Kurtarma

**Soru:** Yedekten geri dönüş gerçekten çalışıyor mu?

PostgreSQL dökümü ve Elasticsearch snapshot'ı (ADR-0018, 14. bölüm) geçici kopyalara geri yüklenir: geçici veritabanlarına ve adı değiştirilmiş indekslere. Satır ve belge sayıları canlı veriyle, örnek haberlerin metinleri birebir karşılaştırılır; geri yükleme süresi ölçülür. Canlı verinin üzerine tam geri dönüş, uygulamalar durdurularak denenir.

- **Hedef:** Geri dönüş en fazla 2 saatte tamamlanır (RTO); kaybedilen veri en fazla son 24 saattir (RPO) (FOG-10, FOG-11).
- Raporlar `docs/test-raporlari/` altındadır; başlıklar 6.4'teki şablondur.

### 7.4 Kullanılabilirlik ve erişilebilirlik

**Soru:** Arayüz kolay kullanılıyor ve erişilebilir mi?

- **Erişilebilirlik, otomatik:** axe-core, uçtan uca testlerin içinde bütün ekranları WCAG 2.2 AA kurallarına göre tarar. Hedef: kritik ve ciddi düzeyde ihlal bulunmaması.
- **Erişilebilirlik, elle:** Bütün işlemlerin yalnızca klavyeyle yapılabildiği ve temel ekranların bir ekran okuyucuyla kullanılabildiği kontrol edilir. Otomatik araçlar erişilebilirlik sorunlarının yalnızca bir kısmını bulabilir.
- **Kullanılabilirlik:** Uygulamayı daha önce görmemiş en az 3 kişiye görevler verilir (örneğin "son bir haftanın ekonomi haberlerinde 'faiz' kelimesini ara ve bir haberi kaydet") ve görevi yardımsız tamamlayıp tamamlamadıkları gözlemlenir. Ardından System Usability Scale (SUS) anketi uygulanır.
  - **Hedef:** Görevlerin en az %80'inin yardımsız tamamlanması; SUS puanının en az 68 olması.
  - **Neden SUS:** 10 sorudan oluşan, yaygın olarak kabul görmüş standart bir kullanılabilirlik anketi; sonucu 0–100 arası tek bir puandır ve 68, yayımlanmış çalışmalarda ortalama kabul edilen değerdir.
- **Neden axe-core:** Playwright ile birlikte çalışır; erişilebilirlik kontrolü uçtan uca testlere eklenmiş olur. Alternatif Lighthouse, sayfa başına ayrı çalıştırılır ve uçtan uca senaryolar içinde kullanımı daha zordur.

### 7.5 Uyumluluk

**Soru:** Farklı tarayıcı ve ekran boyutlarında çalışıyor mu?

- **Tarayıcılar:** Uçtan uca testler Playwright ile Chromium (Chrome ve Edge'in motoru), Firefox ve WebKit (Safari'nin motoru) üzerinde çalışır (FOG-35).
- **Ekran boyutları:** Uçtan uca testler 360, 768, 1280 ve 1920 piksel genişliklerinde de çalıştırılır (FOG-34).