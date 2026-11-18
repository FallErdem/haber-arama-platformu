# ADR-0018: Geliştirme, Test ve Dağıtım Araçları

- **Durum:** Kabul edildi
- **Tarih:** 2026-11-09
- **İlişki:** ADR-0010'daki MinIO kurulum yöntemini belirler; ADR-0017'deki bağımlılık taraması aracını değiştirir.

## Bağlam

Çalışan iskeletin kurulmasından önce, iş planındaki İ-01 kapsamında altı kararın verilmesi gerekmektedir: yerel Kubernetes ortamı, MinIO'nun kurulum yöntemi, veritabanı geçiş aracı, modül sınırı denetimi, CI tarama araçları ve frontend mimarisi.

## Karar

### 1. Yerel Kubernetes ortamı

- Yerel Kubernetes ortamı olarak **k3d** kullanılır. k3d, uyumluluk testlerinden geçmiş hafif bir Kubernetes dağıtımı olan k3s'i Docker konteynerlerinde çalıştırır.
- k3s ile hazır gelen Traefik devre dışı bırakılır. Dışarıdan gelen trafik **Gateway API** ile yönlendirilir. Gateway API'yi Traefik uygular; Traefik'in kendi kaynak türleri ve Ingress desteği kapatılır.
- Frontend, API ve Keycloak aynı site altında sunulur (örnek: `/`, `/api/`, `/auth/`).
- Yerel ortamda sitenin adresi `http://haber.localhost` adresidir. Tarayıcılar, girişte kullanılan PKCE'nin gerektirdiği şifreleme işlevlerini (`crypto.subtle`) yalnızca güvenli saydıkları adreslerde açar: HTTPS adresleri ve `localhost` ile `.localhost` ile biten adresler. İlk kurulumda kullanılan `http://haber.local` adresinde giriş bu nedenle başlatılamamış, adres 11 Kasım 2026'da değiştirilmiştir. HTTPS, İ-32'de Gateway'de açılacaktır.

Gerekçeler:

- **k3d:** Bilgisayarda Kubernetes'in yanında veri depoları, Keycloak ve uygulamalar da çalışacağından kaynak tüketimi önemlidir (R-24). Kendi uygulamalarımızın imajlarını kümeye aktarmak için yerel bir imaj deposu kurabilir. Kullanılacak bütün Kubernetes kaynakları (Deployment, Service, probe'lar, kaynak sınırları, Secret'lar, Gateway API) standart Kubernetes'teki gibi çalışır.
- **Gateway API:** Kubernetes'te trafiği yönlendirmek için yaygın olarak kullanılan Ingress NGINX, Mart 2026'da emekliye ayrılmıştır ve artık güvenlik güncellemesi almamaktadır. Kubernetes projesi, Ingress'in yerine Gateway API'yi önermektedir.
- **Hazır Traefik'in kapatılması:** Gateway API ve onu uygulayan bileşen ayrıca kurulduğunda sürümler denetim altında olur ve trafiğin kümeye girişi uçtan uca kurulan yapı üzerinden anlatılabilir.
- **Aynı site:** Token bellekte tutulduğundan (ADR-0014) sayfa yenilendiğinde Keycloak oturumu kullanılarak yeniden alınır; bu işlem Keycloak'ın oturum çerezine dayanır. Tarayıcılar farklı sitelere ait çerezleri büyük ölçüde engellediğinden Keycloak uygulamayla aynı sitede sunulur. Aynı site, frontend ile API arasında CORS ihtiyacını da ortadan kaldırır.

Alternatifler:

- **kind:** Standart Kubernetes'in birebir aynısıdır; ancak bu yakınlığın kullanılacak özelliklerde somut bir faydası yoktur ve k3d daha az kaynak tüketir.
- **minikube:** Belgeleri ve eklentileri zengindir; daha fazla kaynak tüketir.

### 2. MinIO'nun kurulum yöntemi

- MinIO uyumlu topluluk çatalı **Silo** (`docker.io/pgsty/silo`) kullanılır; sürüm etiketi sabitlenir.
- Sunucu, yalnızca sunucu programını içeren (distroless) imajla ve root olmayan bir kullanıcıyla çalışır. Kovayı ve kullanıcıları oluşturan iş, `mc` istemcisini içeren standart imajı kullanır.

Gerekçeler:

- Resmi MinIO deposu arşivlenmiştir. Resmi imajlar Docker Hub'dan kaldırılmış, quay.io'da hesapsız erişime kapatılmıştır; son resmi sürüm yalnızca kaynak kod olarak yayımlanmıştır.
- Silo; MinIO'nun S3 ve yönetim API'leri, `MINIO_*` ortam değişkenleri ve disk biçimiyle uyumludur. Güvenlik düzeltmeleri yayımlanmaya devam etmektedir; sürümler değiştirilemez etiketlerle yayımlanır.
- İşçi ve API, MinIO'ya S3 standardı üzerinden eriştiğinden, çatalın bakımı durursa başka bir S3 uyumlu depolamaya kod değişmeden geçilebilir (R-35).

Alternatifler:

- **Resmi MinIO'nun son yayımlanmış imajı:** Hesap gerektirir, güvenlik güncellemesi almaz.
- **Son resmi sürümün kaynak koddan derlenmesi:** Derleme sürecinin bakımı projeye kalır; sonraki güvenlik açıkları için güncelleme gelmez.
- **Diğer üçüncü taraf imajlar** (Chainguard, Bitnami ve benzerleri): Ücretsiz katmanda sürüm sabitlenemez veya imajın kaynağı doğrulanamaz.

### 3. Veritabanı geçiş aracı

- Geçiş aracı olarak **Flyway** kullanılır. Betikler numaralı düz SQL dosyalarıdır (`V1__...sql`) ve deponun kökündeki `db/migrations/` klasöründe tutulur.
- Betikleri Spring Boot API açılırken çalıştırır. Flyway bunun için `news_owner` kullanıcısını kullanır; API'nin normal işlemleri `news_app` kullanıcısıyla yapılır.
- Birden fazla API kopyası aynı anda açılırsa Flyway veritabanında kilit alır; betikleri yalnızca bir kopya çalıştırır.
- Python işçisi, tablolar hazır olana kadar bekleyecek şekilde yazılır.
- Betikler derleme sırasında jar'ın içine `db/migration` klasörüne kopyalanır: `backend/pom.xml`'de `../db/migrations` ek kaynak dizini olarak tanımlıdır. Betiklerin asıl yeri `db/migrations/` olarak kalır; geliştirmede ve imajda aynı yol kullanılır.
- Flyway'in bağlantısı `spring.flyway.url`, `user` ve `password` ayarlarıyla, uygulamanın bağlantısı `spring.datasource` ayarlarıyla ayrı ayrı tanımlanır. Şifreler `DB_OWNER_PASSWORD` ve `DB_APP_PASSWORD` ortam değişkenlerinden okunur; adres `DB_URL` ile değiştirilebilir.
- Testlerde Testcontainers ile `postgres:18.4-trixie` imajı kullanılır (kümedeki PostgreSQL ile aynı sürüm ve aynı Debian tabanı). Kümede CloudNativePG'nin oluşturduğu roller, testte `backend/src/test/resources/db/create-roles.sql` ile oluşturulur.

Gerekçeler:

- **Flyway:** Betiklerin büyük kısmı tetikleyiciler, bölümler ve kullanıcı yetkileri gibi PostgreSQL'e özgü tanımlardır; bunlar düz SQL olarak doğrudan yazılır. Flyway, uygulanmış bir betiğin sonradan değiştirilmesini özet karşılaştırmasıyla tespit eder.
- **`db/migrations/`:** Şemanın sahibi tektir (ADR-0017), ancak ne Spring Boot ne de Python'dur. Betikler Spring Boot projesinin içinde olsaydı, işçi de bu betiklere bağımlı olduğu halde Spring Boot'a aitmiş gibi görünürdü.
- **API tarafından çalıştırılması:** En basit kurulumdur. Bedeli, API'nin `news_owner` bilgilerine sahip olmasıdır. Betiklerin yalnızca bu bilgilere sahip ayrı bir Kubernetes işiyle (Job) çalıştırılması değerlendirilmiş, bu aşamada basitlik tercih edilmiştir.

Alternatif:

- **Liquibase:** Değişiklikleri veritabanından bağımsız olarak tanımlar ve geri alma desteği sunar; ancak daha karmaşıktır ve PostgreSQL'e özgü özellikler bilinçli olarak kullanıldığından veritabanından bağımsızlığa ihtiyaç yoktur.

### 4. Modül sınırı denetimi

- Spring Boot API'nin modül sınırları **Spring Modulith** ile denetlenir. Ana paketin altındaki her paket bir modül kabul edilir; bir test, modüllerin birbirinin iç paketlerine erişip erişmediğini ve döngüsel bağımlılık olup olmadığını kontrol eder.
- Spring Modulith'in modüller arası olay kayıt mekanizması outbox için kullanılmaz: Bu mekanizma aynı uygulamanın içindeki modüller arasında çalışır; outbox kayıtlarını ise ayrı bir uygulama olan Python işçisi işler (ADR-0012).
- Spring Modulith **2.1.1** kullanılır (Spring Initializr'ın Spring Boot 4.1.2 için ürettiği sürüm; `backend/pom.xml`'de sabitlenmiştir). Her modülün sorumluluğu kendi `package-info.java` dosyasında yazılıdır. Sınır testi `ModularityTests` sınıfındadır; aynı sınıf, mimarideki altı modülün tamamının tanındığını da doğrular.
- Python işçisinin paketleri için benzer bir denetim (import-linter) işçinin yapısı netleştikten sonra değerlendirilecektir.

Alternatifler:

- **ArchUnit:** Her türlü mimari kural yazılabilir; ancak modül kurallarının hepsinin elle yazılması gerekir.
- **Maven çok modüllü proje:** İhlalleri derleme sırasında engeller; ancak proje yapısını önemli ölçüde karmaşıklaştırır (ADR-0007).

### 5. CI tarama araçları

| Tarama | Araç | Ne zaman |
|---|---|---|
| Gizli bilgi (FOG-17) | **gitleaks** | Geliştirme bilgisayarında commit öncesinde ve CI'da |
| Bağımlılık açığı (FOG-18); Maven, npm ve Python | **Trivy** | CI'da |
| Konteyner imajları ve Kubernetes yapılandırma dosyaları | **Trivy** | CI'da |
| Bağımlılık güncellemeleri | **Dependabot** | Yeni sürüm çıktığında güncelleme PR'ı açar |

Gerekçeler:

- GitHub'ın kendi gizli bilgi ve kod taraması özel depolarda ücretlidir.
- **gitleaks'in commit öncesinde çalışması:** Bir gizli bilgi push edildikten sonra Git geçmişinden silinmesi yeterli değildir; anahtarın iptal edilip yenilenmesi gerekir (R-16). Commit öncesinde yakalamak sızıntının oluşmasını engeller; CI'daki tarama bu kontrolün atlandığı durumlar için ikinci güvencedir.
- **Trivy:** Bütün ekosistemleri, konteyner imajlarını ve Kubernetes yapılandırma dosyalarını tek araçla tarar. Python için ADR-0017'de seçilen pip-audit'in yerini alır; aynı işi yapan iki aracın raporlarının ve yapılandırmalarının ayrı ayrı yönetilmesi önlenir.

CI kurulurken (İ-09) netleşenler:

- **Araçlar hazır CI adımlarıyla değil, kendi resmi imajlarından sabit sürümle çalıştırılır:** gitleaks v8.30.1 ve Trivy 0.76.1. Böylece CI'da ve geliştirme bilgisayarında aynı komut çalışır ve üçüncü tarafların yazdığı CI adımlarına bağımlılık azalır. Trivy için sarmalayıcı `scripts/ci/trivy.sh` dosyasıdır.
- **gitleaks** CI'da deponun bütün geçmişini tarar. Geliştirme bilgisayarında commit öncesi kontrol `.githooks/pre-commit` dosyasıdır; `git config core.hooksPath .githooks` komutuyla etkinleştirilir.
- **Trivy'de neyin engellediği:** Kendi seçtiğimiz kütüphanelerde (Java, npm, Python) yüksek veya kritik düzeyde açık varsa CI başarısız olur (FOG-18). İmajlardaki işletim sistemi paketleri ve Kubernetes tanımları taranır ve raporlanır, ancak birleştirmeyi engellemez: bunların düzeltilmesi temel imajların yeni sürümlerine ve İ-32'deki sıkılaştırmaya bağlıdır (R-37).
- **Java kütüphaneleri imajdaki jar dosyasından taranır,** `pom.xml`'den değil. Gerçekten dağıtılan kütüphaneler bunlardır ve tarama Maven deposuna istek göndermez. Frontend ve işçi kütüphaneleri kilit dosyalarından (`package-lock.json`, `uv.lock`) taranır.
- **Açık taraması yol filtresiyle ve haftalık çalışır:** Üç imajı derlediği için yalnızca kod, imaj veya Kubernetes dosyaları değiştiğinde çalışır; ayrıca her Pazartesi kendiliğinden çalışır, çünkü kod değişmese de yeni açıklar yayımlanır.
- **Dependabot şimdilik kurulmamıştır.** Sürümler elle güncellenir; haftalık açık taraması, güncelleme gerektiren kütüphaneleri gösterir. İhtiyaç olursa sonradan eklenebilir.

Alternatifler:

- **TruffleHog:** Bulduğu anahtarın geçerli olup olmadığını doğrulayabilir; daha ağırdır ve doğrulama için ilgili servise istek gönderir.
- **OWASP Dependency-Check:** Yalnızca bağımlılıkları tarar, en çok Java için; konteyner imajlarını taramaz.
- Kodun kendisindeki güvenlik hatalarını arayan statik analiz (örneğin Semgrep) şartnamede açıkça istenmemektedir; zaman kalırsa değerlendirilecektir.

### 6. Frontend mimarisi

| Konu | Seçim | Gerekçe | Alternatifler |
|---|---|---|---|
| Derleme aracı | Vite | Uygulama giriş gerektiren tek sayfalık bir uygulamadır, API ayrıdır | Next.js: sunucu tarafında sayfa üretme bu uygulamanın ihtiyacı değildir. |

Not: nginx burada yalnızca statik dosya sunucusu olarak kullanılır; emekliye ayrılan Ingress NGINX bileşeniyle ilgisi yoktur.

İskelet (İ-07) kurulurken netleşenler:

- **TypeScript 6.0.3** kullanılır. Proje şablonu TypeScript 7 ile gelir; ancak ESLint'in TypeScript kodunu okumasını sağlayan `typescript-eslint` eklentisi (8.72) yalnızca TypeScript 6.0'a kadar destekler. Stil denetimi ESLint ile yapılacağından (5. bölüm) desteklenen en yeni TypeScript sürümü seçilmiştir.
- **Giriş:** `oidc-client-ts` ve onu React'e bağlayan `react-oidc-context` kullanılır; akış Authorization Code + PKCE'dir. Token yalnızca bellekte tutulur (ADR-0014); kalıcı tarayıcı deposuna yazılmaz.
- **Sessiz yeniden giriş:** Token bellekte tutulduğundan sayfa yenilendiğinde kaybolur. Sayfa açılırken uygulama, görünmeyen bir çerçevede Keycloak'a ekran göstermeden giriş isteği gönderir; Keycloak oturumu sürüyorsa yeni token alınır, sürmüyorsa giriş düğmesi gösterilir. Bu, Keycloak'ın oturum çerezine ve aynı site kararına dayanır (1. bölüm). Dönüş adresi normal girişle aynıdır (`/oidc-callback`); Keycloak'ta ek bir adres tanımlanmaz.
- **Sunucu verisi** TanStack Query ile alınır; **çeviri** `i18next` ve `react-i18next` ile yapılır, metinler `src/locales/` altındaki dil dosyalarındadır (FOG-31).
- **Testler** Vitest ve React Testing Library ile, jsdom ortamında çalışır; Keycloak ve API taklit edilir. Gerçek Keycloak ile giriş, uçtan uca testlerin konusudur (`08-test-stratejisi.md`).
- **Sonraya bırakılanlar:** Görsel kütüphane (shadcn/ui, Tailwind) ve sayfa yönlendirmesi (React Router, Zod) iskelette kurulmamıştır; kullanıldıkları ilk ekranla birlikte eklenecektir. Kod stili aracı Prettier, İ-09'da eklenecektir. (İkisi de eklendi: Prettier İ-09'da, diğerleri İ-19'da; aşağıya bakın.)
- **Sürümler** `package.json`'da aralık olmadan, kesin olarak yazılır; dolaylı bağımlılıkların sürümleri `package-lock.json` ile sabitlenir.

Arama ve haber detayı ekranları (İ-19, 18 Kasım 2026) kurulurken eklenenler:

| Araç | Sürüm | Ne için | Neden bu, alternatifi |
|---|---|---|---|
| React Router | 8.5.1 | Sayfa adresleri: `/` arama, `/articles/:id` detay, gerisi "bulunamadı" | En basit kullanımıyla (`BrowserRouter`, `Routes`) kurulur. Kendi veri yükleme özelliği kullanılmaz; veriyi TanStack Query getirir, iki araç aynı işi yapmaz. |
| Zod | 4.6.7 | Adres çubuğundaki arama parametrelerinin doğrulanması | Adres kullanıcının değiştirebileceği bir girdidir; her parametrenin geçerli değeri ve geçersizse varsayılanı tek bir şemada yazılıdır. Elle yazılan `if` zincirine göre kısa ve türünü TypeScript'e kendisi verir. Daha küçük `zod/mini` sürümü yazımı daha az okunur olduğu için seçilmedi. |
| Tailwind CSS (`@tailwindcss/vite`) | 4.3.4 | Stil | Sınıflar bileşenin üstüne yazılır, derleme yalnızca kullanılanların CSS'ini üretir. |
| shadcn/ui (stil `aria-nova`) | Komut 4.23.0 | Düğme, seçim kutusu, açılır pencere, takvim, aç/kapa düğmesi, metin kutusu | Paket değildir; bileşenlerin kaynak kodu `src/components/ui/` altına kopyalanır ve projenin parçası olur. Yalnızca kullanılan parçalar alındı. `shadcn` paketi kurulmadı: bir komut satırı aracıdır ve 32 bağımlılık getirirdi; bileşenlerin ihtiyaç duyduğu dokuz CSS tanımı kaynağı yazılarak `index.css`'e alındı. |
| React Aria Components (Adobe) | 1.22.1 | shadcn bileşenlerinin altındaki erişilebilirlik katmanı: klavye, dokunma, ekran okuyucu, odak yönetimi | Radix ve Base UI ile birlikte denendi. WCAG ve klavye davranışı en kapsamlı olanıdır (FOG-30); takvimde Türkçe ay adları ve Pazartesi ile başlayan hafta dil ayarından gelir; takvim için `react-day-picker` ve `date-fns` gerekmez. Radix'in artısı shadcn ile daha yaygın kullanılmasıdır. |
| `@internationalized/date` | 3.12.4 | Takvimin tarih türleri; "Türkiye saatiyle günün başı ve sonu" hesabı | React Aria ile zaten gelir; doğrudan kullanıldığı için aynı sürümle açıkça eklendi. Saat farkı koda yazılmaz, saat dilimi kurallarından hesaplanır. |
| `cn`, `class-variance-authority` | 0.5.2, 0.7.1 | Sınıf adlarını birleştirme; bileşen türlerine göre sınıf tablosu | shadcn bileşenlerinin kullandıkları. `cn` shadcn'in kendi paketidir. |
| `lucide-react` | 1.68.0 | İkonlar | shadcn'in ikon kütüphanesi; shadcn'in seçtiği sürüm aynı gün yayımlanmıştı, iki haftalık sürüme sabitlendi. |
| `@fontsource-variable/newsreader` | 5.3.0 | Başlık ve haber metni yazı tipi | Haber okumak için tasarlanmış, açık lisanslı (OFL) serif yazı tipi; npm paketinden derlemeye girer ve uygulamanın kendi sunucusundan sunulur, Google'a istek gitmez. Türkçe harfler `latin-ext` alt kümesindedir. |
| DOMPurify | 3.4.17 | Haberin tam metninin tarayıcıda ikinci kez temizlenmesi | Tam metin HTML olarak sayfaya basılır. İşçi kaydederken `nh3` ile temizler (FOG-16); işçideki temizlik bir hata yüzünden atlanırsa sayfaya sızan bir betik bellekteki token'ı okuyabilirdi. İzin verilen etiketler işçininkiyle aynıdır. |

- **Görünüm:** Gazete sadeliği; kâğıt rengi zemin, mürekkep rengi metin, tek vurgu rengi (bordo), kart ve gölge yerine ince çizgiler. Renkler `index.css`'te shadcn'in beklediği değişken adlarıyla tanımlıdır; metin renklerinin zemine karşıtlığı WCAG AA'nın 4,5:1 sınırının üzerindedir. Koyu tema şimdilik yoktur.
- **Arama durumu adres çubuğundadır:** İfade, filtreler, sıralama ve sayfa adreste tutulur; geri düğmesi, sayfa yenileme ve paylaşma ek kod gerektirmez. Bozuk bir değer API'ye gitmez, varsayılana döner. Adreste sayfa 1'den başlar, API'de 0'dan; tarihler adreste gün (`2026-11-05`), API'ye Türkiye saatindeki günün başı ve sonu olarak gider.
- **Vurgulama HTML olarak basılmaz:** `<mark>` etiketleri ayrılır, geri kalan metin React'e düz metin olarak verilir.
- **Yeniden deneme:** Sunucunun döndürdüğü hata yeniden denenmez, kullanıcı mesajı hemen görür; yalnızca ağ hataları iki kez daha denenir. TanStack Query'nin varsayılanı her hatayı üç kez dener; kapalı bir arama indeksinde mesaj yaklaşık 7 saniye gecikiyordu.
- **Oturum hataları tek yerde:** 401 alan istek yeniden girişi başlatır (kullanıcı bulunduğu adrese döner); hesap durumunu bildiren 403 hesap bilgisinin yeniden okunmasını tetikler, uygulama hesap durumu ekranına geçer. Oturumu olmayan kullanıcı paylaşılan bir adresi açarsa girişten sonra o adrese döner; dönüş adresi yalnızca uygulamanın kendi yollarından biri olabilir (açık yönlendirme engellenir).

### 7. Yerel ortamdaki altyapı bileşenlerinin kurulumu

| Bileşen | Kurulum | Gerekçe |
|---|---|---|
| Traefik | Helm chart, sürümü sabit | Yalnızca Gateway API desteği açıktır; Traefik'in kendi kaynak türleri, Ingress desteği ve yönetim paneli kapatılmıştır. Yönlendirmeler yalnızca Gateway API ile tanımlandığından Traefik'in yerine başka bir Gateway API uygulaması geçirilebilir |
| PostgreSQL | CloudNativePG operatörü | Asıl kayıt PostgreSQL'dedir; operatör yedekleme ve geri dönüşü hazır sunar. Veritabanı kullanıcıları ve Keycloak veritabanı operatörün kaynaklarıyla tanımlanır. Yedekleme aracını kendi içinde taşıyan "system" imajları kullanımdan kalkmakta olduğundan "standard" imaj kullanılır |
| Elasticsearch, MinIO, Keycloak, Mailpit | Kendi yazılan Kubernetes tanımları, resmi veya bakımı süren imajlarla | Her satır projede yazıldığından anlatılabilir; operatörlerin getirdiği ek kaynak türleri ve pod'lar bu bileşenler için sağladıkları faydadan büyüktür |

- **Bitnami kullanılmaz:** Yaygın kurulum örnekleri Bitnami'nin Helm chart'larını kullanır; ancak Bitnami Ağustos 2025'ten itibaren ücretsiz katmanda sürüm numaralı imajları genel katalogdan kaldırmıştır, bu yüzden sürüm sabitlenemez.
- **Kustomize:** Ortak tanımlar `deploy/k8s/base/`, geliştirme ortamına özgü ayarlar `deploy/k8s/overlays/dev/` altındadır. Kubernetes Secret'ları, depoya girmeyen `secrets/` klasöründeki dosyalardan üretilir; hangi dosyaların gerektiği `secrets.example/` klasöründe gösterilir. CloudNativePG Secret'lara adlarıyla başvurduğundan Kustomize'ın adlara eklediği özet soneki kapatılmıştır.
- **Tek namespace:** Uygulamanın bütün bileşenleri `haber` namespace'indedir; Traefik ve CloudNativePG operatörü gibi küme genelindeki bileşenler kendi namespace'lerindedir.
- **En az yetki:** Elasticsearch'te güvenlik açıktır. Elasticsearch ve MinIO'da işçi ve API için ayrı kullanıcılar bulunur; işçi yazabilir, API yalnızca okuyabilir (ADR-0017). Kullanıcılar, tekrar çalıştırılabilen kurulum işleriyle (Job) oluşturulur.
- **Root olmayan kullanıcı:** MinIO ve Mailpit root olmayan bir kullanıcıyla çalışır; MinIO sunucusu kabuk ve ek araç içermeyen imajla çalışır.
- **Keycloak üretim modunda çalışır:** Geliştirme modunda çalışan bir yapılandırmanın üretim modunda da çalışacağının garantisi yoktur. Küme içinde HTTP kullanılır; HTTPS, trafiğin kümeye girdiği Gateway'de açılacaktır (İ-32).
- **Mailpit dışarıya açılmaz:** Yalnızca geliştirme ortamında, e-postaların gerçek adreslere gitmemesi için kullanılır; arayüzüne `port-forward` ile erişilir.
- **Sürümler sabittir:** k3s v1.36.6+k3s1 (kubectl ile aynı seri), Gateway API v1.6.3, Traefik chart 42.3.1, CloudNativePG chart 0.29.1, PostgreSQL 18.4, Elasticsearch 9.4.9, Silo RELEASE.2026-10-26T00-00-00Z, Keycloak 26.8.2, Mailpit v1.33.1.

Alternatifler:

- **Bütün bileşenler için operatör** (Elasticsearch için ECK, Keycloak Operator): Her operatör kendi kaynak türlerini ve pod'unu getirir; bu ölçekte öğrenilmesi ve işletilmesi gereken bileşen sayısını artırır.
- **Bütün bileşenler için kendi tanımlarımız:** PostgreSQL'in yedekleme ve geri dönüşünün elle kurulması gerekirdi.
- **Kendi uygulamalarımız için Helm chart:** Şablon dili okumayı zorlaştırır; tek bir uygulama için gereğinden fazla esneklik sağlar.

### 8. Keycloak realm'i

- Uygulamanın kullanıcıları Keycloak'ın kendi yönetimi için kullanılan `master` realm'inde değil, ayrı bir `haber` realm'indedir.
- Realm, `deploy/k8s/base/keycloak/realm-haber.json` dosyasında tanımlıdır ve Keycloak açılırken içe aktarılır. Dosya yalnızca projede seçilen ayarları içerir. İçe aktarma yalnızca realm yoksa yapılır; dosya değiştiğinde geliştirme ortamında realm silinip Keycloak yeniden başlatılır.
- **Kayıt ve giriş:** Kullanıcılar kendileri kaydolur, kayıtta bir kullanıcı adı seçer ve kullanıcı adı veya e-postayla giriş yapar. Aynı e-posta iki hesapta kullanılamaz; kullanıcı adı sonradan değiştirilemez. E-posta doğrulanmadan giriş tamamlanamaz. "Beni hatırla" seçeneği yoktur.
- **Şifre:** En az 12 karakter; kullanıcı adıyla ve e-postayla aynı olamaz. Karmaşıklık kuralı yoktur.
- **Kaba kuvvet koruması:** Art arda 5 yanlış denemeden sonra hesap geçici olarak kilitlenir; süre 1 dakikadan 15 dakikaya kadar artar. Kalıcı kilit yoktur.
- **Frontend client'ı (`haber-frontend`):** Şifre saklayamayan, tarayıcıda çalışan bir uygulama olduğundan public client'tır. Yalnızca Authorization Code akışına, PKCE (S256) zorunlu olarak izin verilir. Girişten sonra yalnızca tek ve tam bir adrese geri dönülür; joker karakter kullanılmaz.
- **Hedef kitle:** Access token'ların `aud` alanına `haber-api` eklenir; API bu değeri içermeyen token'ları reddeder.
- **Olaylar:** Kullanıcı ve yönetici olayları kaydedilir; yönetici olaylarının içeriği, gizli bilgi barındırabileceğinden kaydedilmez.
- Giriş ve kayıt sayfaları varsayılan olarak Türkçedir. Geliştirme ortamında e-postalar Mailpit'e gider.

### 9. Spring Boot'ta veri erişim yöntemi

- Spring Boot API, veritabanına Spring'in **`JdbcClient`** sınıfıyla erişir. Sorgular düz ve parametreli SQL olarak yazılır; her tablonun sorguları bir repository sınıfında toplanır. ORM kullanılmaz.
- Eş zamanlı güncellemeler `version` sütunuyla elle denetlenir: güncelleme `WHERE version = ?` koşuluyla yapılır; hiçbir satır etkilenmezse kayıt bu arada başkası tarafından değiştirilmiştir ve istek 409 ile reddedilir.

Gerekçeler:

- Şemanın sahibi Flyway betikleridir (3. bölüm); ORM'in tablo üretme özelliğine ihtiyaç yoktur.
- Sorguların önemli bir kısmı PostgreSQL'e özgüdür (`ON CONFLICT DO NOTHING`, bölümlenmiş ve yalnızca ekleme yapılan audit tablosu); bunlar ORM ile de elle yazılmış SQL gerektirirdi.
- Çalışan SQL kodda açıkça görünür; önbellek, değişiklik takibi ve tembel yükleme gibi görünmeyen davranışlar yoktur.
- Python işçisi de aynı yaklaşımı kullanır (ADR-0017); iki uygulamanın veri erişimi aynı şekilde okunur.

Bedeli, satırların nesnelere çevrilmesinin ve `INSERT`/`UPDATE` cümlelerinin elle yazılmasıdır.

Alternatifler:

- **Spring Data JPA (Hibernate):** Temel kayıt işlemlerini kendisi üretir ve geliştiricinin tanıdığı araçtır; ancak yukarıdaki sorgular için yine SQL yazılması gerekir ve hangi SQL'in ne zaman çalıştığı koddan doğrudan okunamaz.
- **Spring Data JDBC:** ORM'den basittir ve temel kayıt işlemlerini üretir; ancak kayıtları bütün olarak yeniden yazma gibi kendi kuralları vardır ve bu projedeki tablo sayısı için kazancı sınırlıdır.

**API'nin Elasticsearch ve nesne depolama istemcileri (İ-17, İ-18)**

- Elasticsearch'e Spring Boot'un `spring-boot-starter-elasticsearch` bağımlılığıyla (Elasticsearch'in resmi Java istemcisi; sürümü Spring Boot'tan) bağlanılır. Spring Data Elasticsearch kullanılmaz: indeksi ve şablonu işçi yönetir, arama sorgusu elle yazılır (`05-veri-modeli.md`, 5.5); veritabanında ORM kullanılmamasıyla aynı gerekçe.
- MinIO'ya AWS SDK for Java'nın S3 istemcisiyle (`software.amazon.awssdk:s3` 2.57.8; Spring Boot bu kütüphaneyi yönetmez, sürüm `pom.xml`'de sabitlenir) bağlanılır. İşçideki `boto3` ile aynı arayüzdür; ileride başka bir S3 uyumlu depolamaya geçilirse kod değişmez (R-35). MinIO'nun kendi Java istemcisi daha küçüktür ancak ürüne bağlıdır. Asenkron istemci kullanılmadığından Netty'ye dayanan HTTP katmanı bağımlılıktan çıkarılmıştır.
- API iki depoya da yalnızca okuma yetkisi olan kullanıcılarla bağlanır (`news_api`, `news-api`); bu yetki uygulamada değil depoların kendisinde tanımlıdır (7. bölüm).

### 10. Spring Boot API'nin imajı ve dağıtımı

- İmaj `backend/Dockerfile` ile iki aşamada derlenir: ilk aşama JDK ile jar dosyasını üretir, ikinci aşama yalnızca JRE'yi ve jar dosyasını içerir. Derleme araçları ve kaynak kod son imaja girmez. Uygulama imajda root olmayan bir kullanıcıyla çalışır.
- Temel imaj **Eclipse Temurin** `25.0.4.1_1` (`-jdk-noble` ve `-jre-noble`) sürümüdür; geliştirme ortamındaki Java ile aynı sürümdür.
- Derleme bağlamı deponun köküdür, çünkü geçiş betikleri `backend/` dışındadır (3. bölüm). Kökteki `.dockerignore` varsayılan olarak hiçbir dosyayı Docker'a göndermez; yalnızca `backend/` altındaki derleme dosyaları ve `db/migrations/` açılır. Böylece gizli bilgi dosyaları derleme bağlamına girmez.
- Testler imaj derlenirken çalıştırılmaz (Testcontainers Docker gerektirir); `./mvnw verify` ile ve CI'da çalışır.
- İmajın etiketi, derlendiği commit'in kısa özetidir. Etiket geliştirme overlay'inde tutulur ve `scripts/dev/deploy-api.sh` tarafından güncellenir.
- Kubernetes'in kontrolleri Spring Boot Actuator'ın sağlık adreslerini kullanır (`/actuator/health/liveness`, `/actuator/health/readiness`). Yalnızca sağlık adresi açıktır ve token istemez; trafik kuralı yalnızca `/api` ile başlayan adresleri API'ye yönlendirdiği için bu adreslere dışarıdan erişilemez (API sözleşmesi 2.8).
- Kümede API, token imzalarını doğrulayan anahtarları Keycloak'ın küme içindeki adresinden alır; token'ın yayıncısı (`iss`) ise dış adresle karşılaştırılır.

### 11. React frontend'in imajı ve dağıtımı

- İmaj `frontend/Dockerfile` ile iki aşamada derlenir: ilk aşama Node ile uygulamayı derler (`npm ci`, `npm run build`), ikinci aşama yalnızca nginx'i ve derlenmiş dosyaları içerir. Node ve `node_modules` son imaja girmez.
- Derleme imajı `node:26.12.1-alpine`, çalışma imajı `nginxinc/nginx-unprivileged:1.30.6-alpine` sürümüdür. İkincisi, nginx'in kararlı dalının root olmayan kullanıcıyla ve 8080 portunda çalışan resmi imajıdır.
- nginx, dosya karşılığı olmayan her adres için `index.html` dosyasını sunar; girişten dönüş adresi (`/oidc-callback`) bu sayede çalışır. `index.html` önbelleğe alınmaz; adında içerik özeti bulunan derleme çıktıları (`/assets/`) uzun süre önbellekte tutulabilir.
- Derleme bağlamı, etiketleme ve dağıtım API imajıyla aynıdır (10. bölüm); betik `scripts/dev/deploy-frontend.sh` dosyasıdır. Her betik, overlay'de yalnızca kendi imajının etiketini günceller.
- Trafik kuralı `/` ile başlayan bütün istekleri frontend'e yönlendirir. Gateway API'de en uzun eşleşen yol kazandığından `/api` ve `/auth` istekleri API'ye ve Keycloak'a gider.

### 12. Python işçisinin imajı ve dağıtımı

- İmaj `worker/Dockerfile` ile iki aşamada derlenir: ilk aşama uv ile paketleri kilit dosyasındaki sürümlerle kurar, ikinci aşama yalnızca Python'u ve kurulu paketleri içerir. uv ve test araçları son imaja girmez. İşçi imajda root olmayan bir kullanıcıyla çalışır.
- Temel imaj `python:3.14.9-slim-trixie`, uv imajı `ghcr.io/astral-sh/uv:0.13.6` sürümüdür.
- İşçi kümede tek kopya çalışır ve güncelleme yöntemi `Recreate`'tir: yeni sürüm dağıtılırken önce eski pod durdurulur, sonra yenisi başlar. Varsayılan yöntem iki pod'u kısa süre birlikte çalıştırırdı; iki işçi aynı beslemeyi aynı anda okurdu.
- İşçi dışarıdan istek almaz; bu yüzden Service'i ve trafik kuralı yoktur. Sağlık adresleri yalnızca Kubernetes'in kontrolleri içindir.
- Tablolar beklenirken işçi "ayakta ama hazır değil" görünür; Kubernetes onu yeniden başlatmaz.
- Derleme bağlamı, etiketleme ve dağıtım diğer imajlarla aynıdır (10. bölüm); betik `scripts/dev/deploy-worker.sh` dosyasıdır.

## Sonuçlar

- Kurulumda doğrulanacaklar: Flyway'in ücretsiz sürümünün lisans durumu, Spring Modulith'in Spring Boot 4.1 ile uyumlu sürümü, frontend kütüphanelerinin birbiriyle uyumlu sürümleri ve oidc-client-ts'in token'ı bellekte tutma ayarı.
- API, `news_owner` kullanıcısının bilgilerine sahiptir.
- Python işçisinin araçlarından pip-audit çıkarılır; Python bağımlılıkları Trivy ile taranır.
- Geliştiricinin bilgisayarında gitleaks'in commit öncesi kontrolü kurulur; README'de belirtilecektir.