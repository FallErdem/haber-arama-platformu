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
- **Sonraya bırakılanlar:** Görsel kütüphane (shadcn/ui, Tailwind) ve sayfa yönlendirmesi (React Router, Zod) iskelette kurulmamıştır; kullanıldıkları ilk ekranla birlikte eklenecektir. Kod stili aracı Prettier, İ-09'da eklenecektir.
- **Sürümler** `package.json`'da aralık olmadan, kesin olarak yazılır; dolaylı bağımlılıkların sürümleri `package-lock.json` ile sabitlenir.

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