# Riskler

- **Son güncelleme:** 2026-11-03

## 1. Yöntem

### 1.1 Puanlama

Her risk iki boyutta 1–5 arası puanlanır. Puanlar, önlem alınmadan önceki durumu gösterir; böylece hangi önlemlerin vazgeçilmez olduğu görülür.

| Puan | Olasılık (proje süresince) | Etki |
|---|---|---|
| 1 | Çok düşük: %10'dan az | Çok düşük: fark edilmez veya hemen giderilir |
| 2 | Düşük: %10–30 | Düşük: küçük bir aksaklık; bir günden az iş kaybı |
| 3 | Orta: %30–50 | Orta: bir işlev bozulur veya birkaç günlük iş kaybı olur |
| 4 | Yüksek: %50–80 | Yüksek: önemli bir işlev kullanılamaz, veri kaybı olur veya bir haftadan fazla iş kaybı olur |
| 5 | Çok yüksek: %80'den fazla | Çok yüksek: hukuki ihlal, güvenlik ihlali veya projenin başarısız sayılması |

**Önem = Olasılık × Etki**

| Önem | Seviye |
|---|---|
| 1–4 | Düşük |
| 5–9 | Orta |
| 10–14 | Yüksek |
| 15–25 | Kritik |

### 1.2 Yanıt stratejileri

- **Kaçınma:** Riski doğuran şeyi yapmamak.
- **Azaltma:** Olasılığı veya etkiyi düşürmek.
- **Transfer:** Riski başkasına devretmek.
- **Kabul:** Riski bilerek üstlenmek.

### 1.3 Gözden geçirme

Risk kaydı her hafta ilerleme notu yazılırken gözden geçirilir. Yeni riskler eklenir; olasılığı veya etkisi değişen riskler güncellenir. Kapanan riskler silinmez; "Kapandı" olarak işaretlenir ve kapanma nedeni yazılır.

## 2. Risk Kaydı

### 2.1 Kaynak ve Hukuk

| Kimlik | Risk | O | E | Önem | Strateji | Önlem |
|---|---|---|---|---|---|---|
| R-01 | Kaynakların kullanım koşulları veya lisansları değişir. | 2 | 4 | 8 (Orta) | Azaltma | Kaynak araştırması tarihli tutulur; koşullar kaynak eklenirken ve düzenli aralıklarla yeniden kontrol edilir. Gerekirse kaynak devre dışı bırakılır ve içeriği gizlenir (FG-YP-04, FG-YP-09). |
| R-02 | Guardian içerikleri 24 saatten uzun saklanır: silme işi çalışmaz, hata verir veya sistem uzun süre kapalı kalır. **Kapandı (03.11.2026):** Guardian kaynak setinden çıkarıldı (ADR-0006). | 5 | 5 | 25 (Kritik) | Azaltma | Bkz. ADR-0006. |
| R-03 | Bir yayıncı içeriğinin kaldırılmasını talep eder. | 2 | 3 | 6 (Orta) | Azaltma | Haber gizleme işlevi (FG-YP-09), özgün kaynağın her zaman gösterilmesi (FG-AR-07). |
| R-04 | Kullanım hakkı açık bir Türkçe kaynak bulunamaz. **Kapandı (03.11.2026):** TRT Haber, NTV ve CNN Türk, şirket kararıyla kaynak setine alındı (ADR-0004). | 5 | 2 | 10 (Yüksek) | Azaltma | Konu şirkete soruldu; mimari çok dilli tasarlanır (ADR-0003, ADR-0004). |
| R-05 | Lisansı haberin lisansından farklı olan görseller izinsiz gösterilir. **Kapandı (03.11.2026):** Görsel kuralı tüm kaynaklar için değişti; risk R-31 kapsamına alındı. | 4 | 5 | 20 (Kritik) | Azaltma | Bkz. R-31. |
| R-31 | Türk haber kaynaklarının kullanım koşulları, içeriğin (metin ve görseller) saklanmasına ve gösterilmesine izin vermez. | 5 | 5 | 25 (Kritik) | Kabul | Risk şirket tarafından kabul edilmiştir (ADR-0004). Uygulama kapalıdır ve yalnızca geliştirici tarafından kullanılır. Teknik korumalar aşılmaz (FG-VT-06). Özgün kaynak ve özgün habere bağlantı her zaman gösterilir (FG-AR-07). Görseller şirketin talebiyle indirilip yerel nesne depolamada saklanır; risk bu kapsamda da şirket tarafından kabul edilmiştir (ADR-0010). Kaldırma talebinde içerik gizlenir (FG-YP-09). |

### 2.2 Veri Toplama

| Kimlik | Risk | O | E | Önem | Strateji | Önlem |
|---|---|---|---|---|---|---|
| R-06 | Bir beslemenin adresi veya formatı değişir; toplama bozulur. | 5 | 3 | 15 (Kritik) | Azaltma | Kaynak ve besleme sağlık durumu izlenir (FG-YP-06); art arda başarısızlıkta ilgili besleme otomatik devre dışı kalır ve yöneticiye gösterilir (FG-YP-07). Yönlendirmeler sınırlı sayıda takip edilir. Besleme adreslerinin kaynağı (resmi liste veya doğrulama tarihi) ADR-0004'te belgelenir. |
| R-07 | Kaynak bot koruması veya erişim engeli uygular; örneğin çok sayıda besleme isteği nedeniyle toplayıcı engellenir. | 4 | 3 | 12 (Yüksek) | Azaltma | Koruma aşılmaya çalışılmaz (FG-VT-06); besleme hatalı olarak işaretlenir. Aynı kaynağın beslemelerine yapılan istekler, kaynak düzeyindeki bekleme süresine uyularak zamana yayılır; toplama sıklığı besleme bazında ayarlanır (FG-VT-03, FOG-04). Birden fazla kaynak kullanıldığından tek kaynağın kaybı uygulamayı durdurmaz (FOG-08). |
| R-08 | NYT API'nin istek limitleri (API başına günde 500, dakikada 5 istek) aşılır; örneğin zamanlanmış iş birden fazla backend kopyasında aynı anda çalışır. | 4 | 3 | 12 (Yüksek) | Azaltma | Günlük limitin en fazla %80'i zamanlanmış toplamaya ayrılır (FOG-05); istekler arasında en az 12 saniye beklenir. Zamanlanmış işler yalnızca tek kopya çalışan toplayıcı rolünde yürütülür (ADR-0005, ADR-0009). |
| R-09 | NYT API anahtarı iptal edilir; API türündeki tek kaynak kaybedilir. | 1 | 4 | 4 (Düşük) | Azaltma | API şartlarına ve limitlere uyulur (FG-VT-05, FOG-05). CollectAPI, ücretsiz kullanım koşulları doğrulanırsa alternatif API kaynağıdır (ADR-0006). Anahtar iptal edilirse NYT içeriği derhal silinir (FG-YP-14, ADR-0009). |
| R-10 | Aynı haber aynı kaynakta veya farklı kaynaklarda birden fazla kez görünür. Kaynakların kimlikleri tutarsızdır; Türk kaynakları ajans haberlerini büyük ölçüde aynen yayımlar. | 5 | 2 | 10 (Yüksek) | Azaltma | Aynı kaynaktaki tekrarlar kaynak + kimlik birlikteliği ve normalize edilmiş adresle tespit edilir (FG-VT-04). Farklı kaynaklardaki aynı haber gruplanır ve tek sonuç olarak gösterilir (FG-VT-11, FG-AR-10). Farklı kaynak formatları için testler yazılır. |
| R-11 | Sistem kapalıyken veya uyku modundayken toplama yapılmaz; RSS beslemeleri yalnızca son haberleri içerdiğinden aradaki haberler kaçırılır. | 3 | 2 | 6 (Orta) | Azaltma | Geliştirme bilgisayarında otomatik uyku modu kapatılır. Sistem açıldığında bekleyen toplama işleri hemen çalıştırılır. Toplama boşlukları iş kayıtlarından görülebilir (FG-VT-10). Kaçırılan NYT haberleri gerektiğinde Archive API ile elle tamamlanabilir (ADR-0009).
| R-12 | Beslemelerden gelen HTML içerik zararlı betik (XSS) içerir. Örneğin NTV ve Global Voices tam metni HTML olarak veriyor. | 4 | 5 | 20 (Kritik) | Azaltma | HTML içerik izin verilen etiketler listesine göre temizlenir (FOG-16); güvenlik testlerinde zararlı içerikli örnek beslemeler kullanılır. |
| R-32 | Görsel kaynaktan indirilemez; örneğin kaynak görseli kaldırmış, adresini değiştirmiş veya erişimi engellemiştir. | 3 | 2 | 6 (Orta) | Azaltma | İndirilemeyen görselin yerine yer tutucu gösterilir (FG-AR-08). İndirilmiş görseller kaynaktan bağımsız saklandığından sonradan kaybolmaz (ADR-0010). |
| R-33 | Benzerlik tespiti, farklı haberleri yanlışlıkla aynı haber olarak gruplar (örneğin benzer başlıklı ama farklı içerikli haberler). | 3 | 2 | 6 (Orta) | Azaltma | Yalnızca çok benzer haberler gruplanır; asıl haber kayıtları değiştirilmez (FG-VT-11). Gruplama yöntemi, doğru ve yanlış gruplama örneklerinden oluşan bir test setiyle doğrulanır. |

### 2.3 Kimlik, Yetki ve Güvenlik

| Kimlik | Risk | O | E | Önem | Strateji | Önlem |
|---|---|---|---|---|---|---|
| R-13 | Pasif hale getirilen kullanıcı, elindeki geçerli token ile erişmeye devam eder. | 4 | 5 | 20 (Kritik) | Azaltma | Kullanıcı durumu yalnızca token'dan değil, uygulamanın kullanıcı tablosundan kontrol edilir (FG-KY-06, FOG-19); API testleriyle doğrulanır. |
| R-14 | Başka biri, ilk yönetici için yapılandırılan e-posta adresiyle kaydolarak yönetici olur. | 2 | 5 | 10 (Yüksek) | Azaltma | Keycloak'ta e-posta doğrulaması zorunlu tutulur; yöneticilik yalnızca e-postası doğrulanmış kullanıcıya verilir. |
| R-15 | Keycloak kullanıcısı ile uygulamanın kullanıcı kaydı e-posta üzerinden eşleştirilir; e-posta değiştiğinde yetkiler yanlış kişiye geçer. | 2 | 5 | 10 (Yüksek) | Kaçınma | Eşleştirme, Keycloak'ın değişmeyen kullanıcı kimliği (`sub`) ile yapılır. |
| R-16 | Parola, token veya API anahtarı depoya girer. | 3 | 5 | 15 (Kritik) | Azaltma | `.gitignore` ile gizli bilgi dosyaları dışarıda tutulur; CI'da gizli bilgi taraması yapılır (FOG-17). Sızıntı olursa ilgili anahtar derhal iptal edilip yenilenir; yalnızca Git geçmişinden silmek yeterli sayılmaz. |
| R-17 | Kullanılan bağımlılıklarda güvenlik açığı bulunur. | 4 | 4 | 16 (Kritik) | Azaltma | Bağımlılıklar CI'da taranır; yüksek ve kritik açıklar birleştirmeyi engeller (FOG-18). |
| R-18 | Token, parola gibi hassas veriler uygulama loglarına girer (örneğin bir hata mesajının içinde). | 3 | 4 | 12 (Yüksek) | Azaltma | Hassas alanlar log yazılmadan önce maskelenir (FG-AL-04); örnek hata senaryolarında logların hassas veri içermediği testle doğrulanır. |
| R-19 | Audit log kayıtları, veritabanına doğrudan erişen biri tarafından değiştirilir veya silinir. | 2 | 4 | 8 (Orta) | Azaltma | Uygulamanın kullandığı veritabanı kullanıcısına audit kayıtlarında güncelleme ve silme yetkisi verilmez (FG-AL-03). Ek önlemler mimaride belirlenecek. |

### 2.4 Veri ve Altyapı

| Kimlik | Risk | O | E | Önem | Strateji | Önlem |
|---|---|---|---|---|---|---|
| R-20 | Veri birden fazla depoda tutulursa (SQL, NoSQL, arama altyapısı) depolar arasında tutarsızlık oluşur; örneğin gizlenen bir haber arama sonuçlarında görünmeye devam eder. | 3 | 4 | 12 (Yüksek) | Azaltma | Hangi verinin hangi depoda tutulacağı ve depoların nasıl eşitleneceği mimaride belirlenir. Tutarsızlıkları gidermek için yeniden indeksleme imkânı bulunur. |
| R-21 | Süresiz saklanan haberler ve audit log büyüdükçe sorgular yavaşlar. | 3 | 4 | 12 (Yüksek) | Azaltma | Hacim testi büyük deneme verisiyle yapılır (FOG-07); büyüme yönetimi yöntemleri veri büyümesi analizinde belirlenir (FOG-43). |
| R-22 | Veri kaybı yaşanır. | 2 | 4 | 8 (Orta) | Azaltma | Düzenli yedekleme ve düzenli geri dönüş denemesi (FOG-10, FOG-11). |
| R-23 | Disk dolar; veritabanları, loglar veya yedekler yazılamaz hale gelir. Geliştirme bilgisayarında 935 GB'lık diskin 843 GB'ı boştur (03.11.2026). | 1 | 4 | 4 (Düşük) | Azaltma | Disk doluluğu izlenir; %80'i aştığında uyarı üretilir (FOG-41). Saklama süreleri veri büyümesi analizinde belirlenir. |
| R-24 | Geliştirme bilgisayarının kaynakları (16 çekirdek, 30 GB RAM), tüm bileşenleri (Kubernetes, Keycloak, veritabanları, arama altyapısı, nesne depolama, izleme araçları) geliştirme araçlarıyla birlikte aynı anda çalıştırmaya yetmez. | 2 | 3 | 6 (Orta) | Azaltma | Her bileşene kaynak sınırı tanımlanır (FOG-36); bileşen seçiminde kaynak tüketimi bir kriter olarak değerlendirilir; geliştirme sırasında yalnızca gerekli bileşenler çalıştırılır. |
| R-25 | Performans testlerinde yük üreten araç ile test edilen sistem aynı bilgisayarda çalıştığından sonuçlar gerçek bir ortamı yansıtmaz. | 5 | 2 | 10 (Yüksek) | Kabul | Test raporlarında ortam ve bu sınırlama açıkça belirtilir. Yük aracı ile sistem kaynak sınırlarıyla ayrıştırılır. Sonuçlar mutlak değerler yerine karşılaştırmalı yorumlanır (örneğin 1 ve 2 kopya arasındaki fark). |
| R-26 | Kaynaklardan toplanan gerçek haber hacmi, büyük veri hacmi gerektiren testler (FOG-07) için yetersiz kalır. | 5 | 2 | 10 (Yüksek) | Azaltma | Testler için deneme verisi üretilir. Deneme verisi gerçek veriden ayrı tutulur ve açıkça işaretlenir. NYT Archive API'den geçmiş yıllara ait gerçek haberler de kullanılabilir (ADR-0009). |
| R-27 | Geliştirme bilgisayarı arızalanır; push edilmemiş işler kaybolur. | 1 | 4 | 4 (Düşük) | Azaltma | Değişiklikler sık aralıklarla push edilir. Kurulum adımları README'de belgelenir (FOG-38). |
| R-35 | MinIO topluluk sürümü bakım modunda olduğundan, bulunan güvenlik açıkları için güncelleme yayımlanmayabilir. | 3 | 4 | 12 (Yüksek) | Azaltma | Konteyner imajları ve bağımlılıklar CI'da taranır (FOG-18). MinIO'ya yalnızca uygulamanın bileşenleri erişir, küme dışına açılmaz. S3 uyumlu API kullanıldığından gerekirse başka bir S3 uyumlu depolamaya geçilebilir (ADR-0010). |

### 2.5 Proje

| Kimlik | Risk | O | E | Önem | Strateji | Önlem |
|---|---|---|---|---|---|---|
| R-28 | Kullanılan teknolojilerle ilk kez çalışılması nedeniyle işler planlanandan uzun sürer. | 4 | 3 | 12 (Yüksek) | Azaltma | İşler küçük parçalara bölünür; haftalık ilerleme notunda takılınan yerler yazılır ve plan gözden geçirilir. |
| R-29 | Kapsam kontrolsüz genişler; temel işlevler tamamlanmadan yeni özelliklere geçilir. | 4 | 3 | 12 (Yüksek) | Azaltma | Her yeni özellik önce gereksinimler dokümanına önceliğiyle birlikte yazılır. Must öncelikli işler tamamlanmadan Could öncelikli işlere geçilmez. |
| R-30 | Keycloak, JWT doğrulama ve Kubernetes gibi entegrasyonlarda çıkan sorunlar geç fark edilir. | 3 | 4 | 12 (Yüksek) | Azaltma | Özellik geliştirmeye geçmeden önce tüm temel bileşenleri uçtan uca birbirine bağlayan çalışan bir iskelet kurulur. |
| R-34 | Kod değişikliği PR açılmadan doğrudan `main` dalına gönderilir; PR'da çalışan CI kontrolleri atlanır. | 3 | 3 | 9 (Orta) | Azaltma | CI, PR'lara ek olarak `main` dalına yapılan her gönderimde de çalışır; böylece kural dışı bir gönderim fark edilir (ADR-0008). |