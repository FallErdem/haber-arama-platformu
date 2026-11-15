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

### 9. Kategori eşlemesi (İ-11)

Bir haberin ortak kategorileri `CategoryResolver` ile bulunur (ADR-0004, FG-VT-12, FG-VT-13). Kategorilerin veritabanına yazılması toplama akışındadır (İ-12).

Eşleme tablosu hazırlanmadan önce 42 beslemenin tamamı okundu; 42 beslemenin hepsi yanıt verdi (NTV'nin `galeri` ve `video` beslemeleri boştu). Gözlenen kategori değerleri ve karşılıkları `V13__seed_category_mappings.sql` betiğindedir.

- **Kategori değerinin geldiği yer:** NTV ve Global Voices kategori etiketi verir. TRT Haber ve CNN Türk vermez; kategori haber adresindedir (`trthaber.com/haber/ekonomi/...`, `cnnturk.com/video/dunya/...`). Okuyucu, etiketi olmayan haberde adresin klasör kısımlarını (haberin kendi adı hariç) kategori adayı olarak döndürür. Eşleme tablosunda bulunmayan adaylar (`haber`, `video`) kendiliğinden elenir.
- **İki düzey:** Beslemenin varsayılan kategorisi `FEED` düzeyinde atanır. Besleme haber düzeyi eşleme kullanıyorsa (`feeds.use_item_categories`), haberin kategori değerleri eşleme tablosundan ortak kategoriye çevrilir ve `ITEM` düzeyinde atanır. Aynı kategori iki düzeyde de bulunursa `FEED` kalır.
- **Diğer kuralı:** Atanan kategoriler arasında hiç konu kategorisi (`categories.kind = 'TOPIC'`) yoksa haber Diğer'e atanır. Son Dakika bir zaman etiketi olduğundan konu sayılmaz: konusu bulunamayan bir son dakika haberi hem Son Dakika'yı hem Diğer'i alır.
- **Yoruma dayanan eşlemeler:** Çevre haberleri (TRT `cevre`, Global Voices `Environment`) Yaşam'a, TRT `savunma` Gündem'e, TRT `turk-dunyasi` Dünya'ya eşlendi.
- **Türkçe küçük harf:** Kategori değerleri karşılaştırılmadan önce kaynağın dilinin kurallarıyla küçük harfe çevrilir. Python'un `str.lower()` fonksiyonu "I" harfini "i" yapar ve "İ" harfini iki karaktere çevirir; Türkçe kaynaklar için `turkish_lower` fonksiyonu kullanılır.

### 10. Kaydetme ve toplama akışı (İ-12)

Bu iş kalemiyle işçi haber toplamaya başladı. Eklenen kütüphaneler: `httpx` 0.28.1 (HTTP istemcisi) ve test için `respx` 0.23.1 (sahte HTTP yanıtları; testler kaynak sitelere gitmez).

Bir beslemenin okunması (`IngestionService.ingest`):

1. `ingestion_runs` tablosuna okumanın başladığı yazılır (`RUNNING`).
2. Kaynağın istek sırası alınır ve besleme indirilir.
3. İçerik okunur (8. bölüm), her haberin kategorileri bulunur (9. bölüm) ve haberler kaydedilir.
4. Okumanın sonucu ve beslemenin yeni durumu birlikte yazılır.

**Kaydetme (FG-VT-04)**

- Bir haber dört tabloya tek işlemde yazılır: haber (`articles`), kategorileri (`article_categories`), indirilecek görselleri (`media`, `PENDING`) ve Elasticsearch'e aktarım notu (`outbox_events`, ADR-0012). Biri yazılamazsa hiçbiri yazılmaz.
- Tekrar kontrolü `ON CONFLICT DO NOTHING` ile yapılır: aynı kaynaktan aynı kimlikli veya aynı normalleştirilmiş adresli haber zaten varsa satır eklenmez, hata oluşmaz ve ilk kayıt değişmez. Önce "var mı" diye sorup sonra eklemek yerine doğrudan eklemenin denenmesi, iki işlemin arasına başka bir eklemenin girmesi ihtimalini ortadan kaldırır.
- Tekrar gelen haberin kendisi değişmez, ancak bu okumada bulunan kategorilerden eksik olanlar kayıtlı habere eklenir. Bir haber birden fazla beslemede yer alabilir (önce `gundem`, sonra `sondakika`) ve her beslemenin kategorisini taşımalıdır; aksi halde haberin Son Dakika'da görünmesi hangi beslemenin önce okunduğuna bağlı kalırdı. Bu durum ilk gerçek toplamada görüldü (15 Kasım 2026: TRT Haber `sondakika` beslemesindeki 60 haberden 57'si daha önce başka beslemelerden kaydedilmişti ve Son Dakika kategorisini almamıştı). İki kural: Diğer kategorisi sonradan eklenmez; kategori eklendiğinde arama indeksinin güncellenmesi için outbox'a yeni bir not yazılır.
- Haberin ilk yaşam döngüsü durumu yayın tarihine göre belirlenir (30 güne kadar `HOT`, 1 yıla kadar `WARM`, daha eskisi `COLD`; ADR-0011). Eski tarihli haber veren beslemeler vardır (TRT Haber `koronavirus`: 2023).
- Her haber kendi işlemindedir. Verinin kendisinden kaynaklanan bir hata (örneğin saklanamayan bir karakter) yalnızca o haberi atlatır; diğer haberler kaydedilir ve atlanan haber `items_failed` içinde sayılır.

**İndirme (`FeedFetcher`)**

- İşçi kendini `HTTP_USER_AGENT` ayarındaki adla tanıtır (varsayılan `HaberAramaPlatformu/0.1 (egitim projesi)`); tarayıcı gibi görünmeye çalışmaz (FG-VT-05).
- En fazla 3 yönlendirme takip edilir.
- İki zaman sınırı vardır: `httpx`'in aşama başına sınırı (`HTTP_TIMEOUT_SECONDS`, varsayılan 10) ve indirmenin tamamı için toplam sınır (`HTTP_TOTAL_TIMEOUT_SECONDS`, varsayılan 30). `httpx`'in sınırı bağlanma ve yanıt bekleme gibi her aşamaya ayrı ayrı uygulandığından, çok yavaş ama hiç durmayan bir yanıtı tek başına kesmez.
- Koşullu istek: kaynağın verdiği `ETag` ve `Last-Modified` değerleri saklanır ve bir sonraki istekte geri gönderilir. Kaynak 304 dönerse içerik işlenmez; okuma `NOT_MODIFIED` olarak kaydedilir.
- İndirici karar vermez: sonucu "içerik geldi", "değişmedi" veya nedeniyle birlikte "başarısız" olarak döndürür. Ne yapılacağına toplama akışı karar verir.

**İstek sınırlayıcı (`SourceRateLimiter`)**

- Aynı kaynağa iki istek arasında `sources.request_interval_seconds` kadar beklenir; süre önceki isteğin bitişinden sayılır.
- Her kaynağın kendi kilidi vardır: aynı kaynağın beslemeleri sırayla, farklı kaynaklar aynı anda okunur.
- Sınırlayıcı tektir; ileride görsel indirme işi de (İ-14) aynı nesneyi kullanacaktır.

**Hata yönetimi (ADR-0013, 4. bölüm)**

| Durum | Okuma kaydı | Besleme |
|---|---|---|
| İçerik geldi | `SUCCEEDED` | Hata sayacı sıfırlanır; sonraki okuma beslemenin sıklığı kadar sonra |
| Değişmedi (304) | `NOT_MODIFIED` | Hata sayacı sıfırlanır; sonraki okuma beslemenin sıklığı kadar sonra |
| İstek sınırı (429) | `FAILED` | Hata sayacı artmaz; okuma, beslemenin sıklığı ile kaynağın `Retry-After` ile istediği süreden uzun olanı kadar ertelenir |
| Diğer hatalar | `FAILED` | Hata sayacı artar; yeniden deneme 1., 2. ve 3. hatadan sonra 1, 5 ve 15 dakika, 4. hatadan sonra yine 15 dakika sonra; 5. hatada besleme devre dışı kalır |

- "Diğer hatalar": erişim engeli (401, 403), diğer hata kodları, ağ hataları, zaman aşımı, RSS veya Atom olarak tanınmayan içerik ve öngörülmeyen hatalar.
- Erişim engeli aşılmaya çalışılmaz (FG-VT-06): aynı istek, aynı adla ve yalnızca yeniden deneme süreleriyle tekrarlanır.
- 429 hata sayılmaz, çünkü besleme bozuk değildir; kaynak daha seyrek gelinmesini istemektedir.
- ADR-0013 üç yeniden deneme süresi verir, devre dışı bırakma ise 5. hatadadır; 4. hata için son süre (15 dakika) kullanılır.
- Otomatik devre dışı bırakma (FG-YP-07): beslemenin kapatılması (`disabled_reason = 'AUTO'`), audit kaydı ve okuma kaydı tek işlemde yazılır. Sayaç artırılırken besleme satırı kilitlenir (`FOR UPDATE`); okuma sürerken yöneticinin elle kapattığı bir besleme "otomatik kapatıldı" olarak işaretlenmez.
- Audit kaydı: `actor_type = SYSTEM`, `action = FEED_AUTO_DISABLED`, `target_type = FEED`, hedef beslemenin kimliği; `details` içinde yalnızca art arda hata sayısı ve son hatanın metni bulunur.

**Zamanlayıcı**

- Her turda okuma zamanı gelmiş beslemeler kaynağa göre gruplanır; her kaynak ayrı bir görevde okunur. Bir beslemenin hatası ne kendi kaynağının sıradaki beslemelerini ne de diğer kaynakları durdurur (FOG-08).
- Sağlık kontrolü turun bitmesine değil, zamanlayıcının çalışıyor olmasına bakar: her beslemeden sonra canlılık işareti yenilenir. İlk turda 42 beslemenin okunması istek aralıkları nedeniyle 90 saniyeden uzun sürer; işçi bu sırada da hazır görünür.
- Durdurma istendiğinde elindeki besleme bitirilir, sıradakilere başlanmaz. Bir besleme en kötü durumda 40 saniye sürebildiği için (10 saniye bekleme, 30 saniye indirme) pod'a kapanması için 60 saniye tanınır (`terminationGracePeriodSeconds`).

**Sonraya bırakılanlar**

- `ingestion_runs.trigger` şimdilik her okumada `SCHEDULED` yazılır. Elle başlatılan toplamanın ayırt edilmesi yönetim ekranıyla birlikte ele alınacaktır (İ-22).
- Her beslemede yeni bir veritabanı bağlantısı açılır; bağlantı havuzu gerek görülürse eklenecektir.

## Sonuçlar

- Spring Boot API'nin zamanlanmış işi olmadığından, kopya sayısı kısıtsız artırılabilir.
- Projeye ikinci bir dil ve araç zinciri eklenir; testler, kod stili denetimi, bağımlılık taraması ve konteyner imajı Python için ayrıca kurulur.
- İki uygulamanın aynı veri yapılarını farklı yorumlaması riski oluşur (R-36).
- Python'un yerleşik küçük harfe çevirme fonksiyonu Türkçe kurallarını bilmediğinden, Türkçe metinler için ayrı bir fonksiyon yazılır.
- Python işçisi, Kubernetes'in sağlık kontrolleri için küçük bir HTTP uç noktası sunar (FOG-13).