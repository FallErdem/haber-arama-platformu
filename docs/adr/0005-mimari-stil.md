# ADR-0005: Mimari Stil — Modüler Monolit ve İki Çalışma Rolü

- **Durum:** Kabul edildi; roller arası iletişim yöntemi ADR-0013 ile belirlendi; modül adları ADR-0015 ile değiştirildi
- **Tarih:** 2026-11-03

## Bağlam

Şartname backend için Spring Boot kullanılmasını sabit tutmakta; mimari yapı, servis sayısı ve katmanları geliştiriciye bırakmaktadır. Uygulama Kubernetes üzerinde çalışacaktır.

Projenin belirgin iş alanları vardır ve bunlar şartnamenin bölümleriyle örtüşür: kimlik ve yetki, veri toplama, arama, kullanıcıya özel işlevler, yönetim paneli ve audit log. Proje tek geliştirici tarafından yürütülmektedir.

Gereksinimlerden üçü, zamanlanmış işlerin kullanıcı isteklerinden ayrı çalışmasını gerektirmektedir:

- **Kaynaklara giden isteklerin katlanması (FOG-05, R-07, R-08):** Zamanlanmış toplama işleri birden fazla backend kopyasında aynı anda çalışırsa, kaynaklara ve API'ye giden istekler kopya sayısıyla katlanır. Ayrıca aynı haber birden fazla kopya tarafından eş zamanlı olarak kaydedilmeye çalışılabilir.
- **Ölçeklenebilirlik testi (FOG-06):** Backend kopya sayısı artırıldığında kapasitenin nasıl değiştiği ölçülecektir. Toplama işleri aynı süreçte çalışırsa ölçümü etkiler.
- **Hata yalıtımı (FOG-08):** Toplamada oluşan bir hata, uygulamanın diğer işlevlerini etkilememelidir.

## Değerlendirilen Seçenekler

### 1. Katmanlı monolit

Tek uygulama; kod teknik katmanlara göre paketlenir.

- Artı: En basit yapıdır; öğrenme kaynaklarının çoğu bu yapıyı kullanır.
- Eksi: Farklı iş alanlarının kodları aynı paketlerde karışır; proje büyüdükçe bir değişikliğin etkisini görmek zorlaşır.
- Eksi: Zamanlanmış işler her kopyada çalışır; tek kopyada çalışmalarını sağlamak için ayrıca bir kilit mekanizması gerekir.

### 2. Modüler monolit, tek çalışma rolü

Tek uygulama; kod iş alanlarına göre modüllere ayrılır. Modüller birbirine yalnızca dışa açtıkları arayüzler üzerinden erişir.

- Artı: Tek uygulamanın basitliği korunur; modül sınırları kodu düzenli tutar.
- Artı: Spring Boot dokümantasyonu iş alanına göre paketlemeyi tipik yerleşim olarak gösterir; alan bazlı yapıyı zorunlu kılmak için Spring Modulith'i önerir.
- Eksi: Zamanlanmış işler her kopyada çalışır; ayrıca bir kilit mekanizması gerekir.
- Eksi: Ölçeklenebilirlik testi sırasında toplama işleri aynı süreçte çalışır.

### 3. Modüler monolit, iki çalışma rolü

2. seçenekteki kod yapısı; ancak aynı uygulama iki rolde çalıştırılır: kullanıcı isteklerini karşılayan API rolü ve zamanlanmış işleri yürüten toplayıcı rolü.

- Artı: 2. seçeneğin kod düzeni korunur.
- Artı: Toplayıcı rolü tek kopya çalıştığından zamanlanmış işler doğal olarak tek kez çalışır.
- Artı: API rolü, toplama işlerinden bağımsız olarak ölçeklendirilip ölçülebilir.
- Artı: Toplayıcıdaki bir hata kullanıcı isteklerini etkilemez.
- Artı: Twelve-Factor App ilkelerindeki süreç türleri ayrımına (web ve worker süreçleri) karşılık gelir.
- Eksi: Kubernetes'te iki dağıtım birimi yönetilir.
- Eksi: API rolünden toplayıcı rolüne yönelik işlemler (örneğin toplamanın elle başlatılması) bir metot çağrısıyla değil, roller arası bir iletişim yoluyla yapılır.

### 4. Mikroservisler

Her iş alanı ayrı bir uygulama olur; her biri kendi veritabanına sahiptir ve diğerleriyle ağ üzerinden haberleşir.

- Artı: Her servis bağımsız ölçeklenir, dağıtılır ve hata verir.
- Eksi: Servisler arası ağ hataları, birden fazla veritabanında veri tutarlılığı ve dağıtık izleme ihtiyacı gibi önemli bir karmaşıklık getirir.
- Eksi: Bu karmaşıklığın getirdiği faydalar, birden fazla ekibin aynı ürün üzerinde bağımsız çalıştığı durumlarda değerlidir; tek geliştiricili bu projede maliyet faydadan büyüktür.

## Karar

3. seçenek uygulanacaktır: **modüler monolit, iki çalışma rolü.**

### Modüller

Başlangıç modülleri şunlardır; modüllerin sorumlulukları ve aralarındaki ilişkiler mimari dokümanında ayrıntılandırılacaktır:

- **kimlik:** Kullanıcı tablosu, kullanıcı durumları ve yetki kontrolü
- **toplama:** Kaynaklar, beslemeler, RSS/Atom ve API okuyucuları, kategori eşlemesi
- **arama:** İndeksleme, arama ve kaynaklar arası tekrar eden haberlerin gruplanması
- **kullanici:** Haber kaydetme ve kaydedilmiş aramalar
- **yonetim:** Yönetim paneli işlevleri ve istatistikler
- **audit:** Denetim kayıtları

Modül kuralları:

- Bir modül, başka bir modülün iç sınıflarına doğrudan erişmez; yalnızca o modülün dışa açtığı arayüzleri kullanır.
- Her modülün içinde controller, service ve repository katmanları bulunur.
- Modül sınırlarına uyulduğu otomatik olarak denetlenir. Kullanılacak araç teknoloji seçimlerinde belirlenecektir.

### Çalışma rolleri

- **API rolü:** Kullanıcı ve yönetici isteklerini karşılar. Birden fazla kopya çalışabilir.
- **Toplayıcı rolü:** Zamanlanmış işleri yürütür: haber toplama, kaynaklar arası haber gruplama ve diğer arka plan işleri. Her zaman tek kopya çalışır.

İki rol aynı kod tabanından, aynı derleme çıktısından çalışır; hangi rolde başlatılacağı yapılandırmayla belirlenir. İki rol aynı veri depolarını kullanır.

## Sonuçlar

- Tek bir kod tabanı ve tek bir derleme süreci vardır.
- Zamanlanmış işlerin tek kez çalışması için ayrıca bir kilit mekanizmasına ihtiyaç duyulmaz.
- API rolü, toplama işlerinden bağımsız olarak ölçeklendirilebilir ve test edilebilir.
- Kubernetes'te iki ayrı dağıtım birimi tanımlanacaktır.
- Toplamanın elle başlatılması (FG-YP-08) gibi roller arası işlemlerin nasıl iletileceği mimari dokümanında belirlenecektir.
- Toplayıcı rolü tek kopya çalıştığından, çökmesi durumunda yeniden başlatılana kadar yeni haber toplanmaz; kullanıcılar mevcut haberlerde arama yapmaya devam eder. Toplayıcının ileride birden fazla kopyaya çıkarılması gerekirse, işlerin kopyalar arasında paylaştırılması için ek bir mekanizma gerekecektir.
- Modüler yapı, ihtiyaç doğduğunda bir modülün ayrı bir servise çıkarılmasını kolaylaştırır.

## Kaynaklar

- Spring Boot dokümantasyonu, "Structuring Your Code": https://docs.spring.io/spring-boot/reference/using/structuring-your-code.html
- Martin Fowler, "MonolithFirst": https://martinfowler.com/bliki/MonolithFirst.html
- The Twelve-Factor App, "Concurrency": https://12factor.net/concurrency