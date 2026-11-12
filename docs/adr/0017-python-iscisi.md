# ADR-0017: Arka Plan İşlerinin Python İşçisine Taşınması

- **Durum:** Kabul edildi; bağımlılık taraması aracı ADR-0018 ile Trivy olarak değiştirildi
- **Tarih:** 2026-11-05
- **İlişki:** ADR-0005'teki toplayıcı rolünü değiştirir. ADR-0012, ADR-0013 ve ADR-0016'da toplayıcı rolüne verilen işler Python işçisine geçer.

## Bağlam

ADR-0005'te zamanlanmış işler, Spring Boot uygulamasının ayrı bir rolde ve tek kopya çalışan toplayıcı rolüne verilmişti. 05.11.2026 tarihli görüşmede, toplama ile kullanıcı isteklerinin aynı backend'de yürütülmesinin aşırı yük oluşturduğunu belirtmiş; toplama işinin ayrı bir Python uygulamasıyla yapılmasını ve bu uygulamanın veriyi doğrudan veritabanına yazmasını istenilmiştir.

## Karar

### 1. Uygulamalar ve görevleri

| Uygulama | Görevi | Kopya sayısı |
|---|---|---|
| Spring Boot API | Yalnızca kullanıcı ve yönetici isteklerini karşılar; zamanlanmış işi yoktur | Birden fazla |
| Python işçisi | Bütün arka plan işlerini yürütür: haber toplama, görsel indirme, outbox kayıtlarının Elasticsearch'e aktarılması, yaşam döngüsü güncellemesi, kaynak içeriğinin silinmesi ve temizlik işleri | Tek |

### 2. Tarayıcı otomasyonu kullanılmaz

Kaynakların hepsi RSS, Atom veya API sunduğundan Selenium gibi tarayıcı otomasyonu araçlarına şu anda ihtiyaç yoktur.

### 3. Uygulamalar arası iletişim

- İki uygulama yalnızca veri depoları üzerinden iletişim kurar.
- Elle toplama, beslemenin bir sonraki okuma zamanının güncellenmesiyle (ADR-0013); kaynak içeriğinin silinmesi, kaynağa bir silme talebi zamanı yazılmasıyla istenir.
- Veritabanı şeması, Elasticsearch belge yapısı ve sabit değer kümeleri, iki uygulama için de bağlayıcı olarak `05-veri-modeli.md` dokümanında tanımlanır.

### 4. Şemanın sahipliği

Veritabanı geçiş betikleri tek bir yerde tutulur. Python işçisi şemayı hiçbir zaman değiştirmez.

### 5. En az yetki

| Depo | Spring Boot API | Python işçisi |
|---|---|---|
| PostgreSQL | `news_app` kullanıcısı | `news_worker` kullanıcısı; yalnızca ihtiyaç duyduğu tablolarda ve işlemlerde yetki |
| Elasticsearch | Yalnızca okuma | Okuma ve yazma |
| MinIO | Yalnızca okuma | Okuma, yazma ve silme |

### 6. Python sürümü ve araçlar

- **Python 3.14.** Python 3.15, karar tarihinde bir aylıktır ve bazı kütüphaneler bu sürüm için henüz hazır olmayabilir. 3.14 hata düzeltme desteği almaya devam etmektedir.
- Python işçisi depoda `worker/` klasöründe bulunur.

| Araç | Görevi | Gerekçe ve alternatifler |
|---|---|---|
| uv | Python sürümünü kurar, sanal ortamı oluşturur, bağımlılıkları bir kilit dosyasına yazar | Bu işlerin hepsini tek bir araç yapar; kilit dosyası herkesin aynı paket sürümlerini ve özetlerini almasını sağlar (FOG-38). pip ve venv kilit dosyası üretmez; Poetry Python sürümünü yönetmez. |
| asyncio | Tek süreç içinde birbirini beklemeden çalışan görevler | İşçinin işi büyük ölçüde ağdan yanıt beklemektir. İş parçacıkları paylaşılan veriler için kilit yönetimi gerektirir; Celery gibi görev kuyrukları ayrı bir mesaj aracısı gerektirir ve zamanlama zaten veritabanında yapılmaktadır. |
| httpx | HTTP istemcisi | asyncio ile çalışır; aşama bazında zaman aşımı ve en fazla yönlendirme sayısı ayarlanabilir. requests asyncio ile çalışmaz; aiohttp yalnızca asyncio ile çalışır. |
| psycopg 3 | PostgreSQL bağlantı kütüphanesi | asyncio desteği vardır ve SQL'in açıkça yazılmasına izin verir. Şemanın sahibi Python olmadığından bir ORM'in tabloları Python'da yeniden tanımlaması istenmemiştir. |
| feedparser | RSS ve Atom ayrıştırıcı | Bütün RSS sürümlerini ve Atom'u aynı yapıya çevirir; bozuk XML'de durmak yerine bunu bildirir. Yerleşik XML ayrıştırıcılarıyla her format için ayrıştırma kodu ayrıca yazılmalıdır. |
| nh3 | HTML temizleyici | İzin verilen etiketler listesiyle çalışır (FOG-16). bleach artık geliştirilmemektedir; düzenli ifadelerle HTML temizlemek güvenlik açığı bırakır. |
| elasticsearch | Elasticsearch istemcisi | Sunucu sürümleriyle uyumlu yayımlanır; toplu indeksleme yardımcıları outbox aktarımında kullanılır. |
| boto3 | S3 uyumlu depolama istemcisi | MinIO dahil her S3 uyumlu depolamayla çalışır; ileride başka bir depolamaya geçilirse kod değişmez (R-35). |
| Pillow | Görsel işleme | Dosyayı gerçekten bir görsel olarak açmayı deneyerek doğrular; genişlik ve yükseklik bilgisini de verir. Yalnızca ilk baytlara bakan kütüphaneler boyut bilgisi vermez. |
| ruff | Kod stili denetimi ve biçimlendirme | İki işi tek araçla yapar (FOG-28). |
| mypy | Tür kontrolü | Tür ipuçlarını CI'da zorunlu kılar; pyright benzer yetenekte, ancak Node.js gerektirir. |
| pytest | Test çerçevesi | Test verisi hazırlama (fixture), aynı testi farklı girdilerle çalıştırma, asyncio testleri ve kapsam ölçümü (FOG-23). |
| pip-audit | Bağımlılık açığı taraması | Paketleri açık açık veritabanlarına karşı tarar (FOG-18). |

Kütüphane sürümleri kurulum sırasında sabitlenecek; yukarıdaki bilgiler kütüphanelerin resmi sayfalarından doğrulanmıştır.

### 7. İskelet (İ-08)

İskelet, işçinin ileride yapacağı işlerin çatısıdır. Henüz haber çekmez; yalnızca şunları yapar:

- Ayarlarını ortam değişkenlerinden okur. Veritabanı şifresi (`DB_PASSWORD`) verilmemişse ne eksik olduğunu söyleyip durur.
- Veritabanına yalnızca `news_worker` kullanıcısıyla bağlanır.
- Tablolar hazır olana kadar bekler. Tabloları Spring Boot API kurar; işçi ondan önce başlarsa çökmez, birkaç saniyede bir yeniden bakar.
- 30 saniyede bir, okuma zamanı gelmiş ve etkin beslemeleri bulur ve sayısını loga yazar. Bir turda hata olursa (örneğin veritabanına ulaşılamazsa) hata loga yazılır ve sonraki turda yeniden denenir; işçi durmaz.
- Kubernetes'in sağlık kontrollerine iki adresten cevap verir: `/healthz/live` (işçi ayakta mı) ve `/healthz/ready` (tablolar görünüyor ve son tur başarılı mı).
- Kapatılması istendiğinde elindeki turu bitirip kapanır.
- Loglarını, API gibi, her satırı bir JSON nesnesi olacak biçimde yazar.

İskelette alınan kararlar:

- **Yalnızca kullanılan kütüphaneler kuruldu.** Şimdilik tek çalışma bağımlılığı `psycopg` 3.3.6'dır. Yukarıdaki tablodaki diğer kütüphaneler (httpx, feedparser, nh3, elasticsearch, boto3, Pillow), onları kullanan iş kalemleriyle birlikte eklenecektir. Geliştirme araçları: pytest 9.2.0, pytest-asyncio 1.4.1, pytest-cov 7.1.0, ruff 0.17.3, mypy 2.4.1, testcontainers 4.15.0. uv sürümü 0.13.6'dır.
- **Her turda yeni bir veritabanı bağlantısı açılır.** 30 saniyede bir bağlantı açmak ucuzdur ve veritabanı yeniden başlasa bile işçi ek kod gerekmeden toparlanır. Toplama akışı geldiğinde (İ-12) bağlantı havuzu değerlendirilecektir.
- **Testler PostgreSQL üzerinde çalışır.** Test başlarken geçici bir PostgreSQL 18.4 konteyneri açılır, roller oluşturulur ve `db/migrations/` altındaki betikler sırayla uygulanır. Böylece işçi, gerçekte göreceği tablolar ve yetkilerle sınanır; örneğin kullanıcı tablosunu okuyamadığı testle gösterilir.
- **pip-audit kullanılmaz;** Python bağımlılıkları Trivy ile taranır (ADR-0018).

## Sonuçlar

- Spring Boot API'nin zamanlanmış işi olmadığından, kopya sayısı kısıtsız artırılabilir.
- Projeye ikinci bir dil ve araç zinciri eklenir; testler, kod stili denetimi, bağımlılık taraması ve konteyner imajı Python için ayrıca kurulur.
- İki uygulamanın aynı veri yapılarını farklı yorumlaması riski oluşur (R-36).
- Python'un yerleşik küçük harfe çevirme fonksiyonu Türkçe kurallarını bilmediğinden, Türkçe metinler için ayrı bir fonksiyon yazılır.
- Python işçisi, Kubernetes'in sağlık kontrolleri için küçük bir HTTP uç noktası sunar (FOG-13).