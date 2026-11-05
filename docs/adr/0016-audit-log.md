# ADR-0016: Audit Log Tasarımı

- **Durum:** Kabul edildi
- **Tarih:** 2026-11-04

## Bağlam

Şartname audit log için şu soruların cevaplanmasını istemektedir: Hangi işlemler kaydedilir ve hangi bilgiler tutulur, kayıtların sonradan değiştirilemediği nasıl sağlanır, parola ve token gibi hassas verilerin loglara girmemesi nasıl sağlanır?

İlgili gereksinimler: FG-AL-01–05, FG-YP-10, FG-YP-11. İlgili riskler: R-18, R-19.

Kullanıcılar Keycloak'ta oturum açtığından, uygulama oturum açma olayının kendisini görmez; yalnızca sonrasında gelen token'lı istekleri görür.

## Değerlendirilen Seçenekler

### Değiştirilemezlik

- **Veritabanı yetkileri ve tetikleyici:** Uygulamanın ve yanlış yetkiyle bağlanan kullanıcıların değişiklik yapması engellenir. Veritabanının tam yetkili kullanıcısının yapacağı değişiklikler engellenemez.
- **Ek olarak hash zinciri ve zincir özetinin veritabanı dışında saklanması:** Tam yetkili kullanıcının yaptığı değişiklikler de tespit edilebilir. Ek sütunlar, kayıtları sırayla mühürleyen ve zinciri doğrulayan işler, ayrı bir veritabanı kullanıcısı ve veritabanı dışında değiştirilemez bir depolama alanı gerektirir.

### Kimliği doğrulanamayan istekler (401)

- **Audit log'a yazılması:** Bütün reddedilen istekler tek yerde görülür. Ancak isteğin sahibi bilinmez ve çok sayıda geçersiz istek gönderilerek silinemeyen audit tablosu doldurulabilir.
- **Uygulama loglarına ve metriklere yazılması:** Audit tablosu korunur; ani artışlar uyarı ile fark edilir.

## Karar

### 1. Kaydedilen işlemler

- FG-AL-01'deki işlemler kaydedilir. Bunlara ek olarak yeni oturum, kullanıcı kaydının oluşturulması ve beslemenin otomatik olarak devre dışı kalması da kaydedilir.
- **Reddedilen istekler:** Yalnızca kimliği doğrulanmış kullanıcıların reddedilen istekleri (403) audit log'a yazılır. Kimliği doğrulanamayan istekler (401) uygulama loglarına ve metriklere yazılır; ani artışlarda uyarı üretilir.
- **Oturum açma:**
  - Keycloak'ın olay kayıtları açılır; giriş ve başarısız giriş denemeleri Keycloak'ta kaydedilir.
  - Uygulama, token'daki oturum kimliği (`sid`) kullanıcının son kaydedilen oturum kimliğinden (`users.last_session_id`) farklı olduğunda bir "yeni oturum" kaydı yazar. Güncelleme koşullu yapılır; aynı anda gelen iki istekten yalnızca güncellemeyi başaran istek kaydı yazar.
- Kullanıcıların arama sorguları kaydedilmez (FG-AL-05).

### 2. Kayıt alanları

| Alan | Açıklama |
|---|---|
| `id` | UUIDv7 |
| `occurred_at` | İşlemin zamanı |
| `actor_type` | `USER` veya `SYSTEM` |
| `actor_user_id` | İşlemi yapan kullanıcı; sistem işlemlerinde boş |
| `action` | İşlem kodu (örnek: `USER_APPROVED`, `ARTICLE_HIDDEN`) |
| `target_type`, `target_id` | İşlemin yapıldığı nesne |
| `result` | `SUCCESS` veya `FAILURE` |
| `request_id` | İsteğin kimliği; uygulama loglarıyla eşleştirme için |
| `ip_address` | İsteğin geldiği adres (`inet`) |
| `details` | İşleme özgü ek bilgi (`jsonb`) |

### 3. Değiştirilemezlik

- Uygulamanın veritabanı kullanıcısına `audit_events` tablosunda yalnızca ekleme ve okuma yetkisi verilir.
- Tablodaki her güncelleme ve silme bir tetikleyiciyle reddedilir.
- **Sınırlama:** Veritabanının tam yetkili kullanıcısının yapacağı değişiklikler engellenemez ve tespit edilemez. Hash zinciri ve zincir özetinin veritabanı dışında saklanması, getirdiği ek iş nedeniyle bu aşamada uygulanmamıştır; ileride eklenebilecek bir iyileştirmedir.

### 4. Hassas verilerin korunması

- `details` alanına yalnızca her işlem türü için önceden tanımlanmış alanlar yazılır. İstek gövdeleri ve başlıkları hiçbir zaman olduğu gibi kaydedilmez.
- Örnek işlemlerin audit kayıtlarında token, parola veya API anahtarı bulunmadığı testlerle doğrulanır (R-18).

### 5. Kaydın yazılması

- Bir işlem ve o işlemin audit kaydı aynı veritabanı işleminde (transaction) yazılır; işlem yapılıp kaydının oluşmaması mümkün değildir.
- Bir iş işlemine bağlı olmayan kayıtlar (örneğin reddedilen bir istek) ayrı yazılır.

### 6. IP adresi

IP adresi yalnızca doğrudan bağlantı adresinden veya güvenilen bir ağ geçidinin bildirdiği adresten alınır. İstemcinin kendisinin gönderebildiği başlıklara (örneğin `X-Forwarded-For`) güvenilmez.

### 7. Bölümleme ve indeksler

- Tablo `occurred_at` alanına göre aylara bölümlenir. Birincil anahtar `(id, occurred_at)` olur.
- Bölümler geçiş betikleriyle 2028 sonuna kadar önceden oluşturulur. Hiçbir bölüme uymayan kayıtlar için bir varsayılan bölüm bulunur; böylece hiçbir kayıt eklenememe nedeniyle kaybolmaz.
- İndeksler: `occurred_at`; `(actor_user_id, occurred_at)`; `(action, occurred_at)`; `(target_type, target_id)`.

### 8. Saklama süresi

Kayıtların saklama süresi ve süresi dolan bölümlerin arşivlenip arşivlenmeyeceği veri büyümesi analizinde belirlenecektir.

## Sonuçlar

- Uygulama ve geçiş betikleri farklı veritabanı kullanıcılarıyla çalışır (`05-veri-modeli.md`).
- `users` tablosunda `last_session_id` sütunu bulunur. Bu yöntem, Keycloak'ın token'a oturum kimliği (`sid`) eklemesine dayanır; Keycloak kurulurken doğrulanacaktır.
- Aynı kullanıcı birden fazla cihazdan aynı anda çalıştığında, oturumlar arasında geçildikçe birden fazla "yeni oturum" kaydı oluşabilir.
- Başarısız şifre denemeleri uygulamanın audit log'unda değil, Keycloak'ın olay kayıtlarında bulunur.
- Bölümlerin 2028 sonrasına uzatılması için yeni bir geçiş betiği gerekecektir.