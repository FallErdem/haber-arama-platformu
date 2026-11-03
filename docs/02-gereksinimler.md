# Gereksinimler

## 1. Amaç

Bu doküman, uygulamanın fonksiyonel ve fonksiyonel olmayan gereksinimlerini tanımlar. Kapsam, hedef kullanıcılar ve kapsam dışı konular `01-kapsam.md`, kaynak kararları `adr/0003-baslangic-haber-kaynaklari.md` dosyasındadır.

## 2. Tanımlar

### 2.1 Roller

- **Kullanıcı:** Haberlerde arama yapar, haberleri görüntüler ve kaydeder.
- **Yönetici:** Kullanıcının tüm yetkilerine ek olarak kullanıcıları, kaynakları ve sistemi yönetir.

### 2.2 Kullanıcı durumları

- **Onay bekliyor:** Kaydolmuş ancak yönetici tarafından onaylanmamış. Hiçbir işleve erişemez.
- **Aktif:** Rolünün izin verdiği işlevlere erişebilir.
- **Pasif:** Yönetici tarafından erişimi kapatılmış. Hiçbir işleve erişemez.

### 2.3 Öncelik (MoSCoW)

- **Must:** Olmazsa olmaz. Şartnamenin açıkça istediği her şey bu önceliktedir.
- **Should:** Önemli, ancak gerekirse sonraki bir aşamaya ertelenebilir.
- **Could:** Zaman kalırsa yapılır.
- **Won't:** Bu sürümde yapılmayacak (bkz. `01-kapsam.md`, Kapsam Dışı).

### 2.4 Gereksinim kimlikleri

Her gereksinimin benzersiz bir kimliği vardır. Testler bu kimliklere bağlanır.

| Önek | Alan |
|---|---|
| FG-KY | Kimlik doğrulama ve yetkilendirme |
| FG-VT | Veri toplama |
| FG-AR | Arama ve görüntüleme |
| FG-KO | Kullanıcıya özel işlevler |
| FG-YP | Yönetim paneli |
| FG-AL | Audit log |
| FOG | Fonksiyonel olmayan gereksinimler |

## 3. Fonksiyonel Gereksinimler

### 3.1 Kimlik Doğrulama ve Yetkilendirme

| Kimlik | Gereksinim | Öncelik |
|---|---|---|
| FG-KY-01 | Kullanıcı, Keycloak üzerinden kaydolabilmeli, oturum açabilmeli ve oturumunu kapatabilmelidir. | Must |
| FG-KY-02 | Backend, her istekteki JWT'yi Keycloak'ın `/certs` uç noktasından alınan anahtarlarla doğrulamalıdır. İmzası, süresi veya yayıncısı (issuer) geçersiz olan istekler reddedilmelidir. | Must |
| FG-KY-03 | Keycloak'ta uygulama rolü tutulmamalıdır. Kullanıcının rolü ve durumu, uygulama veritabanındaki kullanıcı tablosundan okunmalıdır. | Must |
| FG-KY-04 | İlk kez oturum açan kullanıcı, kullanıcı tablosunda "onay bekliyor" durumunda oluşturulmalıdır. | Must |
| FG-KY-05 | Yetki kontrolü backend'de yapılmalıdır. Rolü yetmeyen, onay bekleyen veya pasif kullanıcıların istekleri reddedilmelidir. | Must |
| FG-KY-06 | Pasif hale getirilen kullanıcının erişimi, elinde geçerli bir token olsa bile kesilmelidir. | Must |
| FG-KY-07 | Uygulama ilk açılışta, yapılandırmada belirtilen e-posta adresine sahip kullanıcıyı aktif yönetici olarak tanımlamalıdır. | Must |

### 3.2 Veri Toplama

| Kimlik | Gereksinim | Öncelik |
|---|---|---|
| FG-VT-01 | Sistem, tanımlı kaynaklardan belirlenen aralıklarla otomatik olarak haber toplamalıdır. | Must |
| FG-VT-02 | RSS 2.0, Atom ve Guardian Open Platform API kaynak türleri desteklenmelidir. | Must |
| FG-VT-03 | Her kaynak için toplama sıklığı, istekler arası bekleme süresi, dil, saklama süresi ve alan eşlemesi (hangi bilginin hangi alandan okunacağı) tanımlanabilmelidir. | Must |
| FG-VT-04 | Aynı haber tekrar toplandığında yeni kayıt oluşturulmamalıdır. Tekrar tespiti kaynak ile kaynağın verdiği kimliğin birlikteliğine, ek olarak haberin normalize edilmiş adresine dayanmalıdır. | Must |
| FG-VT-05 | Toplayıcı, kaynakların robots.txt kurallarına ve tanımlı istek aralıklarına uymalı; isteklerinde kendini kendi adıyla (User-Agent) tanıtmalıdır. | Must |
| FG-VT-06 | Toplayıcı bot koruması veya erişim engeliyle karşılaştığında bunu aşmaya çalışmamalı, hatayı kaydetmelidir. | Must |
| FG-VT-07 | Saklama süresi dolan içerik, kaynağın kuralına göre otomatik olarak silinmeli veya yeniden istenerek yenilenmelidir. | Must |
| FG-VT-08 | Yayın tarihleri UTC'ye çevrilerek saklanmalıdır. | Must |
| FG-VT-09 | Her haberle birlikte kaynak adı, özgün habere bağlantı, varsa yazar ve kaynağın lisans/atıf bilgisi saklanmalıdır. | Must |
| FG-VT-10 | Her toplama işinin sonucu kaydedilmelidir: başlangıç ve bitiş zamanı, yeni ve tekrar eden haber sayısı, varsa hata bilgisi. | Must |

### 3.3 Arama ve Görüntüleme

| Kimlik | Gereksinim | Öncelik |
|---|---|---|
| FG-AR-01 | Kullanıcı haberlerde anahtar kelimeyle arama yapabilmelidir. Arama başlık, özet ve varsa tam metin üzerinde yapılmalı; sonuçların ilgililik sıralamasında başlıktaki eşleşme en yüksek, tam metindeki eşleşme en düşük ağırlığı almalıdır. | Must |
| FG-AR-02 | Arama sonuçları kaynak, tarih aralığı, dil ve kategoriye göre filtrelenebilmelidir. | Must |
| FG-AR-03 | Arama sonuçları sayfalı olarak gösterilmelidir. | Must |
| FG-AR-04 | Arama sonuçları ilgililiğe veya tarihe göre sıralanabilmelidir. | Should |
| FG-AR-05 | Arama sonuçlarında, aranan ifadenin geçtiği bölüm vurgulanarak gösterilmelidir. | Should |
| FG-AR-06 | Haber detayında başlık, varsa tam metin yoksa özet, yayın tarihi, kaynak, varsa yazar ve medya gösterilmelidir. | Must |
| FG-AR-07 | Her haberde özgün kaynağın adı ve özgün habere bağlantı gösterilmeli; kaynağın lisansının gerektirdiği atıf yapılmalıdır. | Must |
| FG-AR-08 | Lisansı gösterime izin vermeyen veya lisansı belirsiz görseller gösterilmemeli, yerine bir yer tutucu gösterilmelidir. | Must |
| FG-AR-09 | Yönetici tarafından gizlenen haberler arama sonuçlarında ve haber detayında görünmemelidir. | Must |

### 3.4 Kullanıcıya Özel İşlevler

| Kimlik | Gereksinim | Öncelik |
|---|---|---|
| FG-KO-01 | Kullanıcı bir haberi kaydedebilmeli ve kaydettiği haberi listeden çıkarabilmelidir. | Must |
| FG-KO-02 | Kullanıcı kaydettiği haberleri sayfalı olarak listeleyebilmelidir. | Must |
| FG-KO-03 | Kaydedilmiş bir haberin içeriği saklama kuralı gereği silindiğinde kullanıcıya bu durum gösterilmelidir. Bu amaçla, kaynağın şartlarının izin vermediği hiçbir içerik saklanmamalıdır. | Must |
| FG-KO-04 | Kullanıcı bir aramayı filtreleriyle birlikte bir adla kaydedebilmeli ve daha sonra tek adımda yeniden çalıştırabilmelidir. | Could |

### 3.5 Yönetim Paneli

| Kimlik | Gereksinim | Öncelik |
|---|---|---|
| FG-YP-01 | Yönetici kullanıcıları listeleyebilmeli ve arayabilmeli; onay bekleyen kullanıcıları onaylayabilmeli veya reddedebilmelidir. | Must |
| FG-YP-02 | Yönetici bir kullanıcıyı pasif veya aktif hale getirebilmeli ve rolünü değiştirebilmelidir. | Must |
| FG-YP-03 | Sistemdeki son aktif yönetici pasif hale getirilememeli ve rolü düşürülememelidir. | Should |
| FG-YP-04 | Yönetici kaynak ekleyebilmeli, düzenleyebilmeli ve devre dışı bırakabilmelidir. | Must |
| FG-YP-05 | Yönetici toplama işlerinin geçmişini ve sonuçlarını görüntüleyebilmelidir. | Must |
| FG-YP-06 | Her kaynağın sağlık durumu (son başarılı toplama zamanı, art arda başarısız deneme sayısı) gösterilmelidir. | Must |
| FG-YP-07 | Belirli sayıda art arda başarısız denemeden sonra kaynak otomatik olarak devre dışı kalmalı ve durum yönetim panelinde gösterilmelidir. | Should |
| FG-YP-08 | Yönetici, zamanlanmış toplamayı beklemeden bir kaynak için toplamayı elle başlatabilmelidir. | Should |
| FG-YP-09 | Yönetici bir haberi gerekçe belirterek gizleyebilmeli ve gizlemeyi geri alabilmelidir. | Should |
| FG-YP-10 | Yönetici audit log kayıtlarını görüntüleyebilmeli, arayabilmeli ve filtreleyebilmelidir. | Must |
| FG-YP-11 | Yönetici filtrelenmiş audit log kayıtlarını CSV olarak dışa aktarabilmelidir. | Should |
| FG-YP-12 | Yönetim panelinde sistem bileşenlerinin durumu ve temel istatistikler (toplam ve kaynak bazında haber sayısı, son 24 saatte toplanan haber sayısı, kullanıcı sayısı) gösterilmelidir. | Must |
| FG-YP-13 | Kaynak eklenirken bağlantı test edilebilmeli ve alan eşlemesinin sonucu örnek bir haber üzerinde önizlenebilmelidir. | Could |

### 3.6 Audit Log

| Kimlik | Gereksinim | Öncelik |
|---|---|---|
| FG-AL-01 | Şu işlemler kaydedilmelidir: oturum açma, yetkisiz erişim denemesi, kullanıcı onaylama/reddetme, durum ve rol değişiklikleri, kaynak ekleme/düzenleme/devre dışı bırakma, elle toplama başlatma, haber gizleme ve gizlemeyi geri alma, audit log dışa aktarma. | Must |
| FG-AL-02 | Her kayıtta işlemi yapan kullanıcı, zaman (UTC), işlem türü, işlemin yapıldığı nesne, sonuç (başarılı/başarısız) ve isteğin kimliği bulunmalıdır. | Must |
| FG-AL-03 | Audit log kayıtları sonradan değiştirilememeli ve silinememelidir. | Must |
| FG-AL-04 | Parola, token gibi hassas veriler audit log'a ve uygulama loglarına girmemelidir. | Must |
| FG-AL-05 | Kullanıcıların arama sorguları kişiye bağlı olarak audit log'a kaydedilmemelidir. | Should |

## 4. Fonksiyonel Olmayan Gereksinimler

### 4.1 Varsayımlar

- **Tasarım kapasitesi:** 500 kayıtlı kullanıcı, en fazla 50 eş zamanlı kullanıcı.
- **Yanıt süresi:** Aksi belirtilmedikçe backend'in isteği alması ile yanıtı göndermesi arasındaki süredir; ağ gecikmesi dahil değildir.
- **p95 / p99:** İsteklerin %95'inin / %99'unun bu süre içinde yanıtlanması.

### 4.2 Performans

| Kimlik | Gereksinim | Öncelik | Doğrulama |
|---|---|---|---|
| FOG-01 | Arama istekleri, 50 eş zamanlı kullanıcı altında p95 ≤ 500 ms ve p99 ≤ 1000 ms içinde yanıtlanmalıdır. | Must | Yük testi |
| FOG-02 | Arama dışındaki okuma istekleri (haber detayı, kaydedilen haberler vb.), 50 eş zamanlı kullanıcı altında p95 ≤ 300 ms içinde yanıtlanmalıdır. | Must | Yük testi |
| FOG-03 | Yük testi süresince başarısız istek oranı %1'in altında olmalıdır. | Must | Yük testi |
| FOG-04 | Varsayılan toplama sıklığı 15 dakikadır ve kaynak bazında değiştirilebilir. Bir haber, kaynakta yayımlanmasından en geç 30 dakika sonra aranabilir olmalıdır. | Must | Entegrasyon testi |
| FOG-05 | Guardian API için günlük istek limitinin en fazla %50'si zamanlanmış toplamaya ayrılmalıdır. Kalan pay elle başlatılan toplama ve yeniden denemeler içindir. | Must | Toplama işi kayıtları |
| FOG-06 | Backend kopya sayısı 1'den 2'ye çıkarıldığında, FOG-01 hedefi korunarak karşılanabilen saniyedeki istek sayısı en az %70 artmalıdır. | Must | Ölçeklenebilirlik testi |
| FOG-07 | FOG-01 ve FOG-02 hedefleri, en az 1 milyon haber ve 10 milyon audit log kaydı içeren deneme verisinde de sağlanmalıdır. Bu hacim, veri büyümesi hesabı yapıldıktan sonra gerekirse güncellenecektir. | Must | Hacim testi |

### 4.3 Güvenilirlik

| Kimlik | Gereksinim | Öncelik | Doğrulama |
|---|---|---|---|
| FOG-08 | Bir kaynağın toplanmasında oluşan hata, diğer kaynakların toplanmasını etkilememelidir. | Must | Dayanıklılık testi |
| FOG-09 | Arama altyapısı erişilemez olduğunda, aramaya bağlı olmayan işlevler (kaydedilen haberler, yönetim paneli vb.) çalışmaya devam etmeli; arama istekleri anlaşılır bir hata ile yanıtlanmalıdır. | Must | Dayanıklılık testi |
| FOG-10 | Veritabanları düzenli olarak yedeklenmelidir. Veri kaybı hedefi (RPO) en fazla 24 saat, yeniden çalışır hale gelme hedefi (RTO) en fazla 2 saattir. | Must | Kurtarma testi |
| FOG-11 | Yedekten geri dönüş düzenli olarak denenmeli ve sonucu raporlanmalıdır. | Must | Kurtarma testi |
| FOG-12 | Yeni sürüm dağıtımı sırasında hizmet kesintisi yaşanmamalıdır. | Must | Dağıtım sırasında yük testi |
| FOG-13 | Her backend bileşeni Kubernetes için liveness, readiness ve startup uç noktaları sunmalıdır. | Must | Entegrasyon testi |

### 4.4 Güvenlik

| Kimlik | Gereksinim | Öncelik | Doğrulama |
|---|---|---|---|
| FOG-14 | Uygulama, OWASP Top 10'un güncel sürümündeki açık türlerine karşı korunmalıdır. | Must | Güvenlik testi |
| FOG-15 | Kullanıcıdan ve kaynaklardan gelen tüm girdiler backend'de doğrulanmalıdır. | Must | Birim ve API testleri |
| FOG-16 | Kaynaklardan gelen HTML içerik, gösterilmeden önce izin verilen etiketler listesine göre temizlenmelidir. | Must | Birim ve güvenlik testleri |
| FOG-17 | Parola, token, API anahtarı gibi gizli bilgiler depoda bulunmamalıdır. CI'da gizli bilgi taraması yapılmalıdır. | Must | CI |
| FOG-18 | Bağımlılıklar CI'da bilinen açıklara karşı taranmalıdır. Yüksek veya kritik seviyede açık bulunması değişikliğin birleştirilmesini engellemelidir. | Must | CI |
| FOG-19 | Pasif hale getirilen kullanıcının erişimi, durum değişikliğinden sonraki en fazla 60 saniye içinde kesilmelidir. | Must | API testi |
| FOG-20 | Küme dışına açılan tüm uç noktalar yalnızca HTTPS üzerinden erişilebilir olmalıdır. | Must | Güvenlik testi |
| FOG-21 | API'ye kullanıcı başına istek hızı sınırı uygulanmalıdır (varsayılan: dakikada 120 istek). | Should | API testi |
| FOG-22 | Yanıtlarda güvenlik başlıkları (Content-Security-Policy, Strict-Transport-Security vb.) bulunmalıdır. | Should | Güvenlik testi |

### 4.5 Bakım Kolaylığı

| Kimlik | Gereksinim | Öncelik | Doğrulama |
|---|---|---|---|
| FOG-23 | Backend'in iş mantığı katmanında birim test satır kapsamı en az %80 olmalıdır. | Must | CI kapsam raporu |
| FOG-24 | Otomatikleştirilebilen testler her değişiklikte CI'da çalışmalı; başarısız test değişikliğin birleştirilmesini engellemelidir. | Must | CI |
| FOG-25 | Veritabanı şema değişiklikleri sürümlenmiş geçiş betikleriyle yapılmalıdır. | Must | CI |
| FOG-26 | API, OpenAPI biçiminde belgelenmeli; belge koddan üretilmeli ve her zaman güncel olmalıdır. | Must | CI |
| FOG-27 | API hata yanıtları tutarlı bir biçimde olmalı ve makine tarafından okunabilir bir hata kodu içermelidir (aday biçim: RFC 9457 Problem Details). | Must | API testi |
| FOG-28 | Kod biçimi ve stili otomatik araçlarla denetlenmelidir. | Should | CI |
| FOG-29 | Commit mesajları ADR-0002'deki kurallara göre otomatik denetlenmelidir. | Should | CI |

### 4.6 Kullanılabilirlik ve Erişilebilirlik

| Kimlik | Gereksinim | Öncelik | Doğrulama |
|---|---|---|---|
| FOG-30 | Arayüz WCAG 2.2 AA düzeyinde erişilebilir olmalıdır. | Must | Erişilebilirlik testi |
| FOG-31 | Arayüz Türkçe olmalıdır. Arayüz metinleri koda gömülmemeli, dil dosyalarından okunmalıdır; yeni bir dil eklemek bileşenlerde değişiklik gerektirmemelidir. | Must | Kod incelemesi |
| FOG-32 | Tarih ve saatler kullanıcıya Türkiye saatiyle (Europe/Istanbul) ve arayüz dilinin biçim kurallarına göre gösterilmelidir. | Must | Birim testi |

### 4.7 Uyumluluk

| Kimlik | Gereksinim | Öncelik | Doğrulama |
|---|---|---|---|
| FOG-33 | Arayüz Chrome, Firefox, Edge ve Safari'nin son iki ana sürümünde çalışmalıdır. | Must | Uyumluluk testi |
| FOG-34 | Arayüz 360 px ile 1920 px arasındaki ekran genişliklerinde düzgün görüntülenmeli ve kullanılabilmelidir. | Must | Uyumluluk testi |

### 4.8 Taşınabilirlik ve Dağıtım

| Kimlik | Gereksinim | Öncelik | Doğrulama |
|---|---|---|---|
| FOG-35 | Tüm bileşenler Kubernetes üzerinde konteyner olarak çalışmalıdır. | Must | Dağıtım |
| FOG-36 | Her bileşen için CPU ve bellek istekleri (requests) ve sınırları (limits) tanımlanmalıdır. | Must | Kod incelemesi |
| FOG-37 | Yapılandırma koddan ayrı tutulmalı ve ortam bazında (geliştirme, test, üretim benzeri) yönetilmelidir. | Must | Kod incelemesi |
| FOG-38 | Depoyu ilk kez gören biri, README'deki adımları izleyerek ek bilgiye ihtiyaç duymadan uygulamayı yerel ortamda kurabilmelidir. | Must | Temiz ortamda kurulum denemesi |

### 4.9 Gözlemlenebilirlik

| Kimlik | Gereksinim | Öncelik | Doğrulama |
|---|---|---|---|
| FOG-39 | Uygulama logları yapılandırılmış biçimde (JSON) üretilmeli ve her istek için bir istek kimliği içermelidir. | Must | Entegrasyon testi |
| FOG-40 | İstek süreleri, hata oranları, toplama işi sonuçları ve kaynak kullanımı metrik olarak toplanmalıdır. | Must | Entegrasyon testi |
| FOG-41 | En az şu durumlarda uyarı üretilmelidir: disk doluluğunun %80'i aşması, bir kaynağın art arda başarısız olması, hata oranının belirlenen eşiği aşması. | Must | Uyarı senaryosu denemesi |

### 4.10 Veri Yönetimi

| Kimlik | Gereksinim | Öncelik | Doğrulama |
|---|---|---|---|
| FOG-42 | Saklama süreleri: Global Voices haberleri süresiz, Guardian içerikleri en fazla 24 saat saklanır. Audit log, uygulama logu ve medya dosyalarının saklama süreleri veri büyümesi analizinde belirlenecektir. | Must | Entegrasyon testi |
| FOG-43 | Veri hacmi arttıkça FOG-01 ve FOG-02 hedefleri korunmalıdır. Bunu sağlayacak yöntemler (bölümleme, arşivleme, indeksleme vb.) veri büyümesi analizinde belirlenecektir. | Must | Hacim testi |