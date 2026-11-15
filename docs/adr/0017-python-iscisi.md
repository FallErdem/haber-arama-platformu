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

### 8. Besleme okuyucusu (İ-10)

Okuyucu (`FeedReader`), bir beslemenin metnini alır ve içindeki her haberi kaynaktan bağımsız ortak bir yapıya (`ParsedArticle`) çevirir. Beslemeyi indirmez ve veritabanına yazmaz; bunlar toplama akışının işidir (İ-12). Bu sayede okuyucu, ağ ve veritabanı olmadan, kaydedilmiş gerçek beslemelerle sınanır.

Bu iş kalemiyle eklenen kütüphaneler: `feedparser` 6.0.14 ve `nh3` 0.3.7.

Okuyucu yazılmadan önce dört kaynaktan on bir besleme indirilip incelendi (13 Kasım 2026). Aşağıdaki kararlar bu incelemeye dayanır; örneklerin birkaç habere kırpılmış halleri `worker/tests/fixtures/feeds/` altındadır.

**Okuma**

- **RSS ve Atom için tek sınıf.** `feedparser` iki biçimi de aynı alan adlarıyla verir; `sources.reader_type` değeri `RSS` de olsa `ATOM` da olsa aynı okuyucu kullanılır.
- **İçerik `feedparser`'a dosya benzeri bir nesne olarak verilir.** Düz metin verildiğinde `feedparser` onu bir adres veya dosya yolu sanıp açmayı dener; bir kaynağın gönderdiği yanıt bu yolla bilgisayardaki bir dosyayı okutabilirdi.
- **Tanınmayan içerik hatadır, boş besleme değildir.** Besleme yerine boş yanıt, düz metin veya bir hata sayfası gelirse okuyucu `FeedParseError` fırlatır. Haber içermeyen geçerli bir besleme (incelemede NTV'nin `galeri` ve `video` beslemeleri) sıfır haberle başarılı sayılır.
- **Zorunlu alanı eksik haber atlanır.** Kimliği, adresi (`http` veya `https`), başlığı veya tarihi olmayan haber atlanır; atlanan haber sayısı sonuçta döner ve loga yazılır. Besleme bu yüzden başarısız sayılmaz.
- **Kimlik:** RSS'te `guid`, Atom'da `id`. Kaynak kimlik vermiyorsa haberin adresi kimlik sayılır.
- **Tarih:** `feedparser` tarihi hangi saat diliminde gelirse gelsin UTC'ye çevirir; okuyucu bunu saat dilimi bilgisi taşıyan bir Python tarihine dönüştürür (FG-VT-08). Yayın tarihi yoksa güncellenme tarihi kullanılır.
- **Tür:** Adresinin yolu `/video/` ile başlayan haber `VIDEO`, diğerleri `ARTICLE` sayılır (CNN Türk'te gözlendi). `GALLERY` için incelemede örnek bulunmadığından kural yazılmadı.

**HTML temizliği (FOG-16)**

- İçerik `nh3` ile, kütüphanenin varsayılan izin verilen etiketler listesi kullanılarak temizlenir; listeden yalnızca `<img>` çıkarılmıştır. Yasaklı liste yerine izin listesi kullanıldığı için, bilinmeyen bir etiket de kendiliğinden elenir.
- İçerikteki `<img>` etiketleri çıkarılır ve adresleri görsel listesine alınır; görseller ayrıca indirilip kendi depomuzdan sunulur (ADR-0010).
- Başlık ve özet düz metne çevrilir; HTML içermezler.
- `feedparser` da kendi içinde HTML temizler. Temizliğin başka bir kütüphanenin varsayılan ayarına bağlı kalmaması için `nh3` yine de uygulanır; testler `nh3` katmanını kaynağın gönderdiği ham HTML ile sınar.

**Görseller**

- Öncelik sırası: kaynağa özgü alan (alan eşlemesi), `<enclosure>` (yalnızca görsel türündekiler), içerikteki `<img>` etiketleri. İlk görsel haberin ana görselidir.
- `media:content` yalnızca başka görsel bulunamadığında kullanılır: Global Voices'ta bu alan küçük bir önizleme resmidir, büyük görsel içeriktedir.
- Aynı görsel farklı parametrelerle tekrar gelirse (NTV: `?width=930&format=webp`) tek sayılır; karşılaştırma adresin parametresiz haliyle yapılır.

**Alan eşlemesi (FG-VT-03)**

- `feedparser` standart dışı etiketleri atar. CNN Türk görseli haberin içindeki `<image>` etiketinde verdiği için bu görsel `feedparser`'ın sonucunda yer almaz.
- `sources.field_mapping` bu tür etiketleri okuyucuya tanıtır. Şu an tek anahtar `image`'dır: ana görselin okunacağı etiketin adı. CNN Türk'ün eşlemesi `{"image": "image"}` olarak `V12` betiğiyle yazıldı; diğer üç kaynak görseli standart alanlarda verdiği için eşlemeleri boştur.
- Eşleme tanımlıysa okuyucu beslemeyi Python'un kendi XML okuyucusuyla ikinci kez açar ve yalnızca o etiketi okur. Değerlendirilen alternatif, `feedparser`'ı bırakıp bütün ayrıştırmayı elle yazmaktı; dört farklı biçim için çok daha fazla kod gerektirdiğinden seçilmedi.
- Python'un XML okuyucusu dış varlıkları yüklemez; iç içe varlıklarla belleği doldurma saldırısına karşı koruma expat 2.4.1'den beri vardır (işçi imajında 2.9.0). Bu yüzden ek bir kütüphane eklenmedi.
- Besleme geçerli bir XML değilse (`feedparser` bozuk XML'i de okuyabilir) haberler özel alan olmadan döner ve durum loga yazılır.

**Adres normalleştirme (FG-VT-04)**

- `articles.normalized_url` için: şema ve alan adı küçük harfe çevrilir, `#` ile başlayan kısım, `utm_` ile başlayan parametreler ve yolun sonundaki eğik çizgi atılır. Yol kısaltılmaz ve diğer parametreler korunur; iki farklı haber aynı adrese inmez.
- Kullanıcıya gösterilen adres haberin özgün adresidir (`articles.url`).

**Tür kontrolü**

- `feedparser` tür bilgisi yayımlamaz ve ayrı bir tür paketi de yoktur. `mypy` ayarında yalnızca bu modül için "tür bilgisi bulunamadı" hatası kapatıldı; `feedparser`'dan gelen değerler okuyucuda tek tek kontrol edilerek kullanılır.

**Bilinen sınırlar**

- TRT Haber'in içerik alanı özetin tekrarından ve bir telif satırından oluşur; olduğu gibi (temizlenerek) saklanır.
- NTV'nin bir görsel adresinde Türkçe karakter bulunuyor. Adresin indirilebilir biçime çevrilmesi görsel indirme işinde (İ-14) ele alınacak.

## Sonuçlar

- Spring Boot API'nin zamanlanmış işi olmadığından, kopya sayısı kısıtsız artırılabilir.
- Projeye ikinci bir dil ve araç zinciri eklenir; testler, kod stili denetimi, bağımlılık taraması ve konteyner imajı Python için ayrıca kurulur.
- İki uygulamanın aynı veri yapılarını farklı yorumlaması riski oluşur (R-36).
- Python'un yerleşik küçük harfe çevirme fonksiyonu Türkçe kurallarını bilmediğinden, Türkçe metinler için ayrı bir fonksiyon yazılır.
- Python işçisi, Kubernetes'in sağlık kontrolleri için küçük bir HTTP uç noktası sunar (FOG-13).