# ADR-0014: Kimlik ve Yetki Akışı

- **Durum:** Kabul edildi; 27 Kasım 2026'da güncellendi (kayıttaki e-posta doğrulaması kaldırıldı, bkz. sondaki "Güncelleme" bölümü)
- **Tarih:** 2026-11-04

## Bağlam

Şartnameye göre kullanıcının kim olduğu Keycloak'tan JWT ile alınır; gelen JWT'ler Keycloak'ın `/certs` uç noktasından alınan anahtarlarla doğrulanır; kullanıcının ne yapabileceğine uygulamanın veritabanındaki kullanıcı tablosu karar verir ve Keycloak'ta uygulama rolü tutulmaz. Yetkisiz bir isteğin backend'de reddedildiği gösterilebilmeli, pasif hale getirilen kullanıcının erişimi kesilmelidir.

İlgili gereksinimler: FG-KY-01–07, FOG-19. İlgili riskler: R-13, R-14, R-15.

## Değerlendirilen Seçenekler

### Frontend'in giriş yöntemi

**Authorization Code + PKCE:** Tarayıcıda çalışan uygulamalar için standart OAuth 2.0 akışıdır. Erişim token'ı frontend'de tutulur ve her istekte backend'e gönderilir.

- Artı: Yaygın ve standarttır; şartnamenin tarif ettiği JWT doğrulama akışıyla birebir örtüşür.
- Eksi: Token tarayıcıda bulunduğundan, sayfaya sızan zararlı bir betik (XSS) token'a erişebilir.

**Backend-for-Frontend (BFF):** Token'ları backend tutar; tarayıcıya yalnızca bir oturum çerezi verilir.

- Artı: Token tarayıcıya hiç ulaşmadığından daha güvenlidir.
- Eksi: Backend'de oturum yönetimi gerektirir; daha karmaşıktır ve şartnamenin tarif ettiği akıştan uzaklaşır.

### Token'ın tarayıcıda saklanması

- **Bellekte:** Sayfaya sızan bir betiğin token'ı okuması zorlaşır; sayfa yenilendiğinde token Keycloak oturumu kullanılarak yeniden alınır.
- **`localStorage`'da:** Sayfa yenilendiğinde korunur, ancak sayfadaki herhangi bir betik tarafından kolayca okunabilir.

### Kullanıcı durumunun kontrolü

- **Her istekte veritabanından:** Pasif hale getirilen kullanıcının erişimi bir sonraki istekte kesilir; her istekte bir veritabanı sorgusu yapılır.
- **Kısa süreli önbellekle:** Veritabanı yükü azalır; durum değişikliği önbellek süresi kadar gecikir.

### E-posta doğrulaması için e-posta gönderimi

- **Mailpit:** Geliştirme için sahte bir SMTP sunucusudur; e-postaları gerçek adreslere göndermeden yakalar ve bir web arayüzünde gösterir.
- **SMTP (Gmail):** E-postalar gerçekten gönderilir; bir uygulama şifresinin gizli bilgi olarak yönetilmesini gerektirir.
- **E-posta doğrulamasının kapatılması:** Ek bileşen gerektirmez, ancak kullanıcıların e-posta adresleri doğrulanmaz.

## Karar

### Keycloak

- Uygulama için ayrı bir realm kullanılır.
- Kullanıcıların kendi kendine kaydolması açıktır; e-posta doğrulaması zorunludur. (27 Kasım 2026'da kaldırıldı, bkz. "Güncelleme".)
- Keycloak'ta uygulama rolü tanımlanmaz.

### Frontend

- Giriş, **Authorization Code + PKCE** akışıyla yapılır; frontend, Keycloak'ta istemci sırrı (client secret) olmayan bir istemci olarak tanımlanır.
- Erişim token'ı **bellekte** tutulur; `localStorage` veya `sessionStorage` kullanılmaz.
- Çıkış yapıldığında Keycloak oturumu da sonlandırılır.

### Backend

- Backend, gelen her istekteki JWT'yi Keycloak'ın `/certs` uç noktasından alınan açık anahtarlarla doğrular. İmzanın yanı sıra token'ın süresi, yayıncısı (`iss`) ve hedef kitlesi (`aud`) de kontrol edilir.
- Açık anahtarlar önbelleğe alınır; token'da tanınmayan bir anahtar kimliği (`kid`) görüldüğünde anahtarlar yeniden alınır. Böylece Keycloak'ın anahtar değişiklikleri desteklenir.
- Kullanıcı, token'daki değişmeyen kimlik (`sub`) ile kullanıcı tablosundaki kaydıyla eşleştirilir; e-posta eşleştirmede kullanılmaz.
- Kullanıcı kaydı yoksa ilk istekte "onay bekliyor" durumunda oluşturulur.
- Kullanıcının rolü ve durumu her istekte veritabanından okunur; başlangıçta önbellek kullanılmaz. Yük testinde darboğaz görülürse, süresi 60 saniyeyi aşmayan bir önbellek eklenebilir (FOG-19).
- Token'ı geçersiz olan istekler `401`, rolü yetmeyen veya durumu aktif olmayan kullanıcıların istekleri `403` ile reddedilir. Arayüzde işlevlerin gizlenmesi yalnızca kullanım kolaylığı içindir, yetki kontrolü backend'de yapılır.

### İlk yönetici

Yapılandırmada belirtilen e-posta adresine sahip ve e-postası doğrulanmış (`email_verified`) kullanıcı, ilk girişinde aktif yönetici olarak tanımlanır. (27 Kasım 2026'dan itibaren e-postanın doğrulanmış olması aranmaz, bkz. "Güncelleme".)

- E-posta adresi `INITIAL_ADMIN_EMAIL` ortam değişkeninden okunur (`newssearch.identity.initial-admin-email`); boşsa kimse kendiliğinden yönetici olmaz. Karşılaştırmada büyük/küçük harf ayrımı yapılmaz.
- Kural yalnızca kullanıcı kaydı oluşturulurken uygulanır; var olan bir kullanıcının rolünü veya durumunu değiştirmez.

### Uygulama ayrıntıları

- Kullanıcı kaydı oluşturulurken e-posta token'daki `email` alanından, görünen ad `name` alanından alınır; `name` yoksa `preferred_username` kullanılır. E-posta içermeyen bir token ile kayıt oluşturulamaz; istek `401` ile reddedilir.
- Rol yetkisi yalnızca durumu aktif olan kullanıcıya verilir. Onay bekleyen, pasif veya reddedilmiş bir kullanıcı, tablodaki rolü ne olursa olsun yetkisizdir; yalnızca `GET /api/v1/me` ile kendi durumunu görebilir.
- `403` yanıtındaki hata kodu kullanıcının durumundan çıkarılır (`USER_PENDING_APPROVAL`, `USER_REJECTED`, `USER_PASSIVE`); kullanıcı aktifse ve rolü yetmiyorsa `FORBIDDEN` döner.

### E-posta gönderimi

- Başlangıçta bütün ortamlarda **Mailpit** kullanılır.
- Üretim benzeri ortam kurulurken **Gmail SMTP** eklenecektir.
- SMTP sunucusu ortam bazında yapılandırılır; bir ortamdan diğerine geçmek yalnızca yapılandırma değişikliği gerektirir.

## Sonuçlar

- Token tarayıcıda bulunduğundan XSS'e karşı önlemler (HTML temizleme ve Content-Security-Policy; FOG-16, FOG-22) bu kararın güvenliği için de önemlidir.
- Her istekte bir veritabanı sorgusu yapılır; etkisi yük testinde ölçülecektir.
- Geliştirme ortamına Mailpit bileşeni eklenir.
- Gmail SMTP eklendiğinde uygulama şifresi bir gizli bilgi olarak yönetilecektir (R-16).

## Güncelleme (27 Kasım 2026): E-posta doğrulaması kaldırıldı

- Mentörün isteğiyle Keycloak'ta kayıttaki e-posta doğrulaması kapatıldı (`realm-haber.json`'da `verifyEmail: false`). Kullanıcı kayıt formunu doldurunca doğrudan uygulamaya döner.
- İlk yönetici kuralı artık `email_verified` aramaz: yapılandırmadaki e-posta adresiyle kaydolan ilk kullanıcı aktif yönetici olur (`UserProvisioningService`).
- Mailpit kalır: Keycloak'ın şifre sıfırlama e-postaları ve Alertmanager'ın uyarı e-postaları ona gider.