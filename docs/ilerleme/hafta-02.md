# Hafta 2 İlerleme Notu (9–13 Kasım 2026)

## Yapılanlar

- Kalan hazırlık dokümanları tamamlandı: test stratejisi, iş planı ve kodlama standartları. Haftanın iş kalemleri GitHub'da issue olarak açıldı.
- Yerel Kubernetes ortamı kuruldu (İ-03): k3d kümesi, Gateway API ve Traefik, PostgreSQL (CloudNativePG), Elasticsearch, MinIO uyumlu görsel deposu, Keycloak ve Mailpit. Her veri deposunda API ve işçi için ayrı yetkili kullanıcılar oluşturuldu ve yetkileri denendi. Kurulum adımları `deploy/README.md` dosyasına yazıldı.
- Veritabanı geçiş betikleri yazıldı ve denendi (İ-04): bütün tablolar, audit log yapısı, kullanıcı yetkileri ve başlangıç verisi (10 kategori, 4 kaynak, 42 besleme).
- Keycloak'ta uygulamaya özel realm yapılandırıldı (İ-05): kayıt, e-posta doğrulama, şifre kuralı, kaba kuvvet koruması ve arayüz için PKCE zorunlu client.
- Spring Boot API'nin iskeleti yazıldı (İ-06): modül yapısı ve modül sınırı testi, açılışta çalışan geçiş betikleri, token doğrulaması, ilk girişte kullanıcı kaydı ve ilk yönetici kuralı, `GET /api/v1/me`, ortak hata biçimi ve istek kimliği. 31 test.
- React arayüzünün iskeleti yazıldı (İ-07): Keycloak ile giriş ve çıkış, sayfa yenilemede sessiz yeniden giriş, hesap durumu ekranı ve çeviri altyapısı. 16 test.
- Python işçisinin iskeleti yazıldı (İ-08): kendi kullanıcısıyla veritabanı bağlantısı, tabloların hazır olmasını bekleme, zamanlayıcı döngüsü ve sağlık adresleri. 39 test.
- Üç uygulama da konteyner imajı olarak paketlenip kümeye dağıtıldı; kayıt olmaktan hesap durumunu görmeye kadar bütün akış tarayıcıda uçtan uca çalıştırıldı.
- CI kuruldu (İ-09): her değişiklikte derleme, testler, test kapsamı eşiği (%80), kod biçimi ve stil denetimi, commit mesajı denetimi, gizli bilgi taraması ve güvenlik açığı taraması otomatik çalışıyor.

## Devam edenler

- İ-10 (RSS ve Atom okuyucuları), İ-11 (kategori eşlemesi) ve İ-12 (kaydetme ve toplama akışı) sırada; bugün içinde tamamlanacak.

## Alınan kararlar

- **Geliştirme ve dağıtım araçları:** Yerel Kubernetes için k3d, trafik için Gateway API ve Traefik, geçiş betikleri için Flyway, CI taramaları için gitleaks ve Trivy; görsel deposu olarak bakımı süren MinIO uyumlu bir sürüm (ADR-0018).
- **Veri erişimi:** Spring Boot'ta `JdbcClient` ile SQL ve repository sınıfları. Şemanın sahibi geçiş betikleri; sorguların önemli kısmı PostgreSQL'e özgü; işçi de aynı yaklaşımı kullanıyor (ADR-0018).
- **İki veritabanı kullanıcısı:** Geçiş betikleri tabloların sahibi olan kullanıcıyla, uygulamanın kendisi yalnızca okuma ve yazma yetkisi olan kullanıcıyla çalışıyor (ADR-0018).
- **Rol yetkisi yalnızca aktif kullanıcıda:** Onay bekleyen, pasif veya reddedilmiş kullanıcı, rolü ne olursa olsun yetkisiz; yalnızca kendi durumunu görebiliyor (ADR-0014).
- **Yerel adres `haber.localhost`:** Tarayıcılar PKCE'nin gerektirdiği şifreleme işlevlerini yalnızca HTTPS ve localhost adreslerinde açıyor (ADR-0018).
- **Token bellekte, sessiz yeniden giriş:** Token kalıcı tarayıcı deposuna yazılmıyor; sayfa yenilendiğinde Keycloak oturumu kullanılarak ekran gösterilmeden yeniden alınıyor (ADR-0018).
- **TypeScript 6:** ESLint'in TypeScript eklentisi henüz TypeScript 7'yi desteklemiyor (ADR-0018).
- **İşçi tek kopya ve `Recreate`:** Yeni sürüm dağıtılırken iki işçinin aynı anda çalışmaması için (ADR-0018).
- **Açık taramasında neyin engellediği:** Kendi seçtiğimiz kütüphanelerdeki yüksek ve kritik açıklar birleştirmeyi engelliyor; imajlardaki sistem paketleri ve Kubernetes tanımlarındaki bulgular raporlanıyor ve kabul edilen risk olarak izleniyor (ADR-0018, R-37).
- **Commit denetimi kendi betiğimizle:** commitlint, tek bir biçim kontrolü için fazla bağımlılık getiriyordu (ADR-0002).

## Öğrenilenler

- **Kaynak sunucusu (resource server):** Giriş ve token üretimi Keycloak'ın işi; API yalnızca gelen token'ı denetliyor: imza, süre, yayıncı (`iss`) ve hedef kitle (`aud`). Şifre yalnızca Keycloak'ın sayfasına yazılıyor; uygulama şifreyi hiç görmüyor.
- **En az yetki:** Her bileşen yalnızca işine yetecek kadar yetkiyle bağlanıyor. API ele geçirilse tablo silemez; işçi ele geçirilse kullanıcı bilgilerini okuyamaz. Bunlar testlerle gösterilebiliyor.
- **Testcontainers:** Test başlarken geçici bir PostgreSQL konteyneri açılıyor, bitince siliniyor. Testler gerçek veritabanı davranışıyla ve gerçek geçiş betikleriyle çalışıyor.
- **Spring Modulith:** Bir test, modüllerin birbirinin iç paketlerine erişip erişmediğini ve döngüsel bağımlılık olup olmadığını denetliyor.
- **DTO:** API, içerideki nesneyi değil yalnızca dışarıya gösterilecek alanları taşıyan ayrı bir kaydı döndürüyor; tablo değişse de API'nin yanıtı kendiliğinden değişmiyor.
- **İki aşamalı konteyner imajı:** İlk aşama derliyor, ikinci aşama yalnızca çalışmak için gerekenleri içeriyor; derleme araçları ve kaynak kod son imaja girmiyor.
- **Kubernetes sağlık kontrolleri:** "Ayakta mı" kontrolü başarısız olursa pod yeniden başlatılıyor; "hazır mı" kontrolü başarısız olursa pod'a istek gönderilmiyor. İşçi tabloları beklerken ayakta ama hazır değil görünüyor.
- **Güvenli bağlam:** Tarayıcılar bazı şifreleme işlevlerini yalnızca HTTPS veya localhost adreslerinde sunuyor.
- **Yol filtreleri:** CI'da yalnızca değişen uygulamanın kontrolleri çalışıyor. PR'larda filtre son commit'e değil, PR'ın tamamında değişen dosyalara bakıyor.

## Takılınan yerler

- İskelet ve CI planlanandan uzun sürdü; kullanılan teknolojilerin çoğuyla ilk kez çalışıldı.
- İlk adres olan `http://haber.local` üzerinde giriş başlatılamadı; neden tarayıcının güvenli bağlam kuralıydı. Adres değiştirildi, realm yeniden içe aktarıldı.
- Proje şablonunun getirdiği TypeScript 7 ile ESLint eklentisi birlikte kurulamadı; TypeScript 6'ya dönüldü.
- Güvenlik açığı taraması, temel imajların içindeki sistem paketlerinde düzeltmesi yayımlanmış bulgular gösterdi; bunlar raporlanıyor ve İ-32'de ele alınacak (R-37).
