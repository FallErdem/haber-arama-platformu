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