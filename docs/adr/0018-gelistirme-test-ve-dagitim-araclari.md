# ADR-0018: Geliştirme, Test ve Dağıtım Araçları

- **Durum:** Kabul edildi
- **Tarih:** 2026-11-09
- **İlişki:** ADR-0010'daki MinIO kurulum yöntemini belirler; ADR-0017'deki bağımlılık taraması aracını değiştirir.

## Bağlam

Çalışan iskeletin kurulmasından önce, iş planındaki İ-01 kapsamında altı kararın verilmesi gerekmektedir: yerel Kubernetes ortamı, MinIO'nun kurulum yöntemi, veritabanı geçiş aracı, modül sınırı denetimi, CI tarama araçları ve frontend mimarisi.

## Karar

### 1. Yerel Kubernetes ortamı

- Yerel Kubernetes ortamı olarak **k3d** kullanılır. k3d, uyumluluk testlerinden geçmiş hafif bir Kubernetes dağıtımı olan k3s'i Docker konteynerlerinde çalıştırır.
- k3s ile hazır gelen Traefik devre dışı bırakılır. Dışarıdan gelen trafik **Gateway API** ile yönlendirilir. Hangi bileşenin kurulacağı kurulum sırasında belirlenecektir.
- Frontend, API ve Keycloak aynı site altında sunulur (örnek: `/`, `/api/`, `/auth/`).

Gerekçeler:

- **k3d:** Bilgisayarda Kubernetes'in yanında veri depoları, Keycloak ve uygulamalar da çalışacağından kaynak tüketimi önemlidir (R-24). Kendi uygulamalarımızın imajlarını kümeye aktarmak için yerel bir imaj deposu kurabilir. Kullanılacak bütün Kubernetes kaynakları (Deployment, Service, probe'lar, kaynak sınırları, Secret'lar, Gateway API) standart Kubernetes'teki gibi çalışır.
- **Gateway API:** Kubernetes'te trafiği yönlendirmek için yaygın olarak kullanılan Ingress NGINX, Mart 2026'da emekliye ayrılmıştır ve artık güvenlik güncellemesi almamaktadır. Kubernetes projesi, Ingress'in yerine Gateway API'yi önermektedir.
- **Hazır Traefik'in kapatılması:** Gateway API ve onu uygulayan bileşen ayrıca kurulduğunda sürümler denetim altında olur ve trafiğin kümeye girişi uçtan uca kurulan yapı üzerinden anlatılabilir.
- **Aynı site:** Token bellekte tutulduğundan (ADR-0014) sayfa yenilendiğinde Keycloak oturumu kullanılarak yeniden alınır; bu işlem Keycloak'ın oturum çerezine dayanır. Tarayıcılar farklı sitelere ait çerezleri büyük ölçüde engellediğinden Keycloak uygulamayla aynı sitede sunulur. Aynı site, frontend ile API arasında CORS ihtiyacını da ortadan kaldırır.

Alternatifler:

- **kind:** Standart Kubernetes'in birebir aynısıdır; ancak bu yakınlığın kullanılacak özelliklerde somut bir faydası yoktur ve k3d daha az kaynak tüketir.
- **minikube:** Belgeleri ve eklentileri zengindir; daha fazla kaynak tüketir.

### 2. MinIO'nun kurulum yöntemi

Resmi MinIO'nun son yayımlanmış sürümü kurulur; kesin sürüm etiketi kurulum sırasında resmi imaj deposundan belirlenecektir.

- Resmi depo arşivlendiğinden bu sürüm güvenlik güncellemesi almaz (R-35). MinIO'ya yalnızca API ve işçi erişir; küme dışına açılmaz ve MinIO'nun kendi OIDC (OpenID Connect - kimlik doğrulama protokolu) girişi kullanılmaz.
- Konteyner imajı taramasının MinIO için bulduğu açıklar, gerekçesiyle birlikte kabul edilen risk olarak işaretlenir.
- İşçi MinIO'ya S3 standardı üzerinden (boto3) eriştiğinden, gerekirse başka bir S3 uyumlu depolamaya kod değişmeden geçilebilir (ADR-0017).

### 3. Veritabanı geçiş aracı

- Geçiş aracı olarak **Flyway** kullanılır. Betikler numaralı düz SQL dosyalarıdır (`V1__...sql`) ve deponun kökündeki `db/migrations/` klasöründe tutulur.
- Betikleri Spring Boot API açılırken çalıştırır. Flyway bunun için `news_owner` kullanıcısını kullanır; API'nin normal işlemleri `news_app` kullanıcısıyla yapılır.
- Birden fazla API kopyası aynı anda açılırsa Flyway veritabanında kilit alır; betikleri yalnızca bir kopya çalıştırır.
- Python işçisi, tablolar hazır olana kadar bekleyecek şekilde yazılır.

Gerekçeler:

- **Flyway:** Betiklerin büyük kısmı tetikleyiciler, bölümler ve kullanıcı yetkileri gibi PostgreSQL'e özgü tanımlardır; bunlar düz SQL olarak doğrudan yazılır. Flyway, uygulanmış bir betiğin sonradan değiştirilmesini özet karşılaştırmasıyla tespit eder.
- **`db/migrations/`:** Şemanın sahibi tektir (ADR-0017), ancak ne Spring Boot ne de Python'dur. Betikler Spring Boot projesinin içinde olsaydı, işçi de bu betiklere bağımlı olduğu halde Spring Boot'a aitmiş gibi görünürdü.
- **API tarafından çalıştırılması:** En basit kurulumdur. Bedeli, API'nin `news_owner` bilgilerine sahip olmasıdır. Betiklerin yalnızca bu bilgilere sahip ayrı bir Kubernetes işiyle (Job) çalıştırılması değerlendirilmiş, bu aşamada basitlik tercih edilmiştir.

Alternatif:

- **Liquibase:** Değişiklikleri veritabanından bağımsız olarak tanımlar ve geri alma desteği sunar; ancak daha karmaşıktır ve PostgreSQL'e özgü özellikler bilinçli olarak kullanıldığından veritabanından bağımsızlığa ihtiyaç yoktur.

### 4. Modül sınırı denetimi

- Spring Boot API'nin modül sınırları **Spring Modulith** ile denetlenir. Ana paketin altındaki her paket bir modül kabul edilir; bir test, modüllerin birbirinin iç paketlerine erişip erişmediğini ve döngüsel bağımlılık olup olmadığını kontrol eder.
- Spring Modulith'in modüller arası olay kayıt mekanizması outbox için kullanılmaz: Bu mekanizma aynı uygulamanın içindeki modüller arasında çalışır; outbox kayıtlarını ise ayrı bir uygulama olan Python işçisi işler (ADR-0012).
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