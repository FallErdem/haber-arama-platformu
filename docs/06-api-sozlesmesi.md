# API Sözleşmesi

## 1. Amaç

Bu doküman, Spring Boot API'nin frontend'e sunduğu uç noktaları ve bütün uç noktalar için geçerli kuralları tanımlar. Kod yazıldıktan sonra uç noktaların güncel ve ayrıntılı referansı, koddan üretilen OpenAPI belgesidir (FOG-26); bu doküman tasarımı ve kuralları anlatır.

## 2. Genel Kurallar

### 2.1 Adres yapısı ve sürüm

- Bütün uç noktalar `/api/v1/` ile başlar.
- Mevcut istemcileri bozacak bir değişiklik (bir alanın kaldırılması veya adının değişmesi, yanıt yapısının değişmesi) gerektiğinde yeni uç noktalar `/api/v2/` altında açılır; eski sürüm bir geçiş süresi boyunca çalışmaya devam eder. Yeni bir alanın eklenmesi uyumsuz değişiklik sayılmaz.
- Frontend ve API aynı adres üzerinden sunulduğundan CORS ayarı gerekmez.

### 2.2 Kimlik doğrulama ve erişim

- Her istek `Authorization: Bearer <token>` başlığını içerir (ADR-0014). İstisna: Görsel uç noktası (bkz. 4.4).
- `GET /api/v1/me` dışındaki bütün uç noktalar yalnızca durumu `ACTIVE` olan kullanıcılara açıktır.
- `/api/v1/admin/` altındaki uç noktalar yalnızca `ADMIN` rolüne açıktır.
- Yetki kontrolü backend'de yapılır; arayüzde işlevlerin gizlenmesi yalnızca kullanım kolaylığı içindir.

### 2.3 Veri biçimi

- İstek ve yanıt gövdeleri JSON'dur, karakter kodlaması UTF-8'dir.
- Alan adları `camelCase` yazılır (örnek: `publishedAt`).
- Tarihler ISO 8601 biçiminde ve UTC olarak döner (örnek: `2026-11-05T09:30:00Z`).
- Sabit değer kümeleri, veri modelindeki değerlerle aynıdır (örnek: `PENDING`, `ACTIVE`).
- Kaynaklar ve kategoriler, kimlikleri yerine kodlarıyla gösterilir (örnek: `NYT`, `SPORTS`).

### 2.4 Sayfalama

- Sayfalı listeler `page` ve `size` parametrelerini alır. `page` 0'dan başlar; `size` varsayılan olarak 20, en fazla 100'dür.
- Sayfalı yanıtların yapısı:

```json
{
  "items": [],
  "page": 0,
  "size": 20,
  "totalElements": 1234,
  "totalPages": 62
}
```

- **Arama sınırı:** Aramada `(page + 1) × size` değeri 10.000'i aşamaz; aşan istekler `400 PAGE_LIMIT_EXCEEDED` ile reddedilir. Arama yanıtlarında `totalElements` en fazla 10.000 olarak sayılır; gerçek sayının daha büyük olabildiği durumlarda yanıttaki `totalRelation` alanı `gte` (en az), tam sayıysa `eq` değerini alır.

### 2.5 Güncelleme kuralları

- `PATCH` istekleri yalnızca gövdede bulunan alanları değiştirir.
- İyimser kilitleme uygulanan kayıtların (kullanıcı, kaynak, besleme) yanıtları `version` alanını içerir. `PATCH` istekleri bu değeri gövdede göndermek zorundadır; kayıt bu arada değişmişse istek `409 VERSION_CONFLICT` ile reddedilir.
- Durum değişiklikleri (onaylama, reddetme, gizleme gibi) `PATCH` ile değil, adı işlemi belirten ayrı uç noktalarla yapılır. Böylece her işlem kendi kurallarıyla doğrulanır ve kendi audit kaydını üretir.
- Arka planda işçi tarafından yürütülen işlemleri başlatan istekler (elle toplama, içerik silme, besleme testi) `202 Accepted` döner.

### 2.6 Hata yanıtları

Hatalar RFC 9457 Problem Details biçiminde (`application/problem+json`) döner. `code` alanı makine tarafından okunur; arayüzdeki metin bu koddan, dil dosyalarıyla üretilir (FOG-27).

```json
{
  "type": "about:blank",
  "title": "Bad Request",
  "status": 400,
  "code": "VALIDATION_FAILED",
  "instance": "/api/v1/articles",
  "errors": [
    { "field": "size", "code": "MAX_VALUE" }
  ]
}
```

- `errors` alanı yalnızca girdi doğrulama hatalarında bulunur.
- Yanıtlar iç ayrıntı içermez: Yığın izi (stack trace), SQL hataları veya iç sınıf adları istemciye gönderilmez.

| Durum | Kod | Ne zaman |
|---|---|---|
| 400 | `VALIDATION_FAILED` | Girdi doğrulama hatası |
| 400 | `PAGE_LIMIT_EXCEEDED` | Arama sayfa sınırının aşılması |
| 400 | `EXPORT_TOO_LARGE` | Dışa aktarılacak kayıt sayısının sınırı aşması |
| 401 | `UNAUTHENTICATED` | Token yok, geçersiz veya süresi dolmuş |
| 403 | `USER_PENDING_APPROVAL` | Kullanıcı onay bekliyor |
| 403 | `USER_REJECTED` | Kullanıcının kaydı reddedilmiş |
| 403 | `USER_PASSIVE` | Kullanıcı pasif |
| 403 | `FORBIDDEN` | Kullanıcının rolü yetmiyor |
| 403 | `MEDIA_URL_INVALID` | Görsel adresinin imzası geçersiz veya süresi dolmuş |
| 404 | `NOT_FOUND` | Kayıt yok veya kullanıcıya görünmüyor |
| 409 | `VERSION_CONFLICT` | İyimser kilitleme çakışması |
| 409 | `INVALID_STATE_TRANSITION` | İşlem kaydın mevcut durumunda yapılamıyor |
| 409 | `LAST_ACTIVE_ADMIN` | İşlem son aktif yöneticiyi kaldıracak (FG-YP-03) |
| 409 | `ALREADY_EXISTS` | Benzersiz olması gereken bir değer zaten var |
| 409 | `SOURCE_MUST_BE_DISABLED` | Kaynak içeriğinin silinmesi için kaynağın önce devre dışı bırakılması gerekiyor |
| 429 | `RATE_LIMITED` | İstek sınırı aşıldı (FOG-21) |
| 500 | `INTERNAL_ERROR` | Beklenmeyen hata |

### 2.7 İstek kimliği

Her yanıt `X-Request-Id` başlığını içerir. Bu değer uygulama loglarında ve audit kayıtlarında da bulunur; bir hatanın loglardaki izini sürmeyi sağlar (FOG-39).

### 2.8 Sağlık uç noktaları

Kubernetes'in kullandığı liveness, readiness ve startup uç noktaları (FOG-13) `/api/v1` altında değildir ve dışarıya açılmaz.

## 3. Kullanıcı Bilgisi

### `GET /api/v1/me`

Oturumdaki kullanıcının bilgilerini döner. Durumu `ACTIVE` olmayan kullanıcılara da açıktır; arayüz, onay bekleyen, reddedilen veya pasif kullanıcıya uygun ekranı bu yanıta göre gösterir.

Kullanıcının ilk isteğinde kullanıcı kaydı oluşturulur (ADR-0014).

```json
{
  "id": "0193f1a2-...",
  "email": "kullanici@ornek.com",
  "displayName": "Erdem",
  "role": "USER",
  "status": "PENDING"
}
```

## 4. Arama ve Haberler

### 4.1 `GET /api/v1/articles` — Arama

| Parametre | Açıklama |
|---|---|
| `q` | Arama ifadesi, en fazla 200 karakter. Boşsa haberler tarihe göre listelenir. |
| `sources` | Kaynak kodları, virgülle ayrılmış (örnek: `TRT,NYT`) |
| `language` | `tr` veya `en` |
| `categories` | Kategori kodları, virgülle ayrılmış |
| `from`, `to` | Yayın tarihi aralığı; `from`, `to`'dan sonra olamaz |
| `sort` | `relevance` (ilgililik) veya `newest` (en yeni). `q` doluysa varsayılan `relevance`, boşsa `newest`; `q` boşken `relevance` yok sayılır. |
| `page`, `size` | Bkz. 2.4 |

- Kategori filtresinde `BREAKING` (Son Dakika) seçiliyse, yalnızca son 6 saatte yayımlanan haberler döner (FG-AR-12).
- İlgililik sıralamasında 1 yıldan eski haberler geriye düşer (ADR-0011).
- Gruplanmış haberler tek sonuç olarak döner (FG-AR-10).

Yanıttaki her öğe:

```json
{
  "id": "0193f1a2-...",
  "title": "Deprem sonrası son durum",
  "highlights": {
    "title": ["<mark>Deprem</mark> sonrası son durum"],
    "summary": ["... bölgede <mark>deprem</mark> sonrası ..."]
  },
  "summary": "Bölgede yaşanan deprem sonrası...",
  "source": { "code": "TRT", "name": "TRT Haber" },
  "language": "tr",
  "itemType": "ARTICLE",
  "categories": ["GENERAL", "BREAKING"],
  "publishedAt": "2026-11-05T08:12:00Z",
  "url": "https://www.trthaber.com/...",
  "image": { "url": "/api/v1/media/0193...?exp=1793800800&sig=...", "width": 1200, "height": 675 },
  "otherSourcesCount": 2
}
```

- `highlights`: Eşleşen kelimeler `<mark>` etiketiyle işaretlenir (FG-AR-05). Metnin geri kalanı backend'de HTML kaçış karakterleriyle güvenli hale getirilir; arayüz `<mark>` dışındaki hiçbir etiketi işlemez. `q` boşsa bu alan bulunmaz.
- `image`: Haberin ana görseli; görsel yoksa veya henüz indirilmemişse `null`, arayüz yer tutucu gösterir (FG-AR-08).
- `otherSourcesCount`: Aynı gruptaki diğer kaynakların sayısı.
- Yanıtın sayfalama alanlarına ek olarak `totalRelation` alanı bulunur (bkz. 2.4).

### 4.2 `GET /api/v1/articles/{id}` — Haber detayı

```json
{
  "id": "0193f1a2-...",
  "title": "...",
  "summary": "...",
  "content": "<p>...</p>",
  "author": "...",
  "url": "https://...",
  "source": {
    "code": "NYT",
    "name": "The New York Times",
    "homepageUrl": "https://www.nytimes.com",
    "attributionText": "Data provided by The New York Times"
  },
  "language": "en",
  "itemType": "ARTICLE",
  "categories": ["WORLD"],
  "publishedAt": "2026-11-05T08:12:00Z",
  "media": [
    { "url": "/api/v1/media/...", "width": 2048, "height": 1365, "caption": "...", "credit": "Tomas Munita for The New York Times" }
  ],
  "otherSources": [
    { "articleId": "...", "source": { "code": "CNNTURK", "name": "CNN Türk" }, "url": "https://..." }
  ],
  "saved": false
}
```

- `content`: Tam metin; işçi tarafından temizlenmiş HTML (FOG-16). Kaynak tam metin vermiyorsa `null`, arayüz özeti gösterir (FG-AR-06).
- `media`: Yalnızca indirilmiş görseller listelenir.
- `saved`: Haberin bu kullanıcı tarafından kaydedilip kaydedilmediği.
- Arayüz, kaynağın koduna göre gerekli atıfı ve logoyu gösterir (FG-AR-07, ADR-0009).
- Gizlenmiş bir haber için `404 NOT_FOUND` döner.

### 4.3 `GET /api/v1/sources` ve `GET /api/v1/categories`

Arama filtreleri için etkin kaynakların (`code`, `name`, `language`) ve kategorilerin (`code`, `kind`, `sortOrder`) listesini döner.

### 4.4 `GET /api/v1/media/{id}` — Görsel

Görselin kendisini döner. HTML'deki `<img>` etiketi istek başlığı ekleyemediğinden bu uç nokta JWT değil, imzalı adres ister.

- **Adres biçimi:** `/api/v1/media/{id}?exp={son geçerlilik zamanı}&sig={imza}`. Adresler yalnızca API yanıtlarında üretilir.
- **İmza:** `id` ve `exp` değerlerinin, API'nin yapılandırmasındaki gizli bir anahtarla hesaplanan HMAC-SHA256 değeri. Anahtar bütün API kopyalarında aynıdır ve bir gizli bilgi olarak yönetilir (R-16).
- **Geçerlilik süresi:** `exp`, üretildiği saatin başlangıcından 2 saat sonradır. Böylece adres 1 ile 2 saat arasında geçerli kalır ve aynı saat içinde üretilen bütün yanıtlarda bir görselin adresi aynı olur; tarayıcı görseli önbellekten kullanabilir.
- **Kontroller:** İmza geçersizse veya süre dolmuşsa `403 MEDIA_URL_INVALID` döner. Görsel indirilmemişse veya ait olduğu haber gizlenmişse `404 NOT_FOUND` döner.
- **Yanıt başlıkları:** Görselin doğrulanmış `Content-Type` değeri, `X-Content-Type-Options: nosniff` ve adresin kalan geçerlilik süresini aşmayan `Cache-Control: private, max-age=...` değeri.
- **Sınırlama:** İmza kullanıcıya bağlı değildir; geçerlilik süresi içinde adresi bilen biri görseli görebilir. Görseller kaynakların herkese açık sayfalarında zaten yayımlanmış olduğundan bu kabul edilmiştir.

## 5. Kişisel İşlevler

### 5.1 Kaydedilen haberler

| Yöntem ve adres | Açıklama | Yanıt |
|---|---|---|
| `GET /api/v1/me/saved-articles` | Kaydedilen haberler, kaydedilme zamanına göre yeniden eskiye, sayfalı (FG-KO-02) | 200 |
| `PUT /api/v1/me/saved-articles/{articleId}` | Haberi kaydeder (FG-KO-01). Zaten kayıtlıysa bir şey değişmez. Haber yoksa veya gizliyse `404`. | 204 |
| `DELETE /api/v1/me/saved-articles/{articleId}` | Kayıttan çıkarır. Kayıtlı değilse bir şey değişmez. | 204 |

Listedeki her öğe:

```json
{
  "articleId": "...",
  "savedAt": "2026-11-05T10:00:00Z",
  "hidden": false,
  "article": { "title": "...", "source": { "code": "NTV", "name": "NTV" }, "publishedAt": "...", "image": null }
}
```

Haber sonradan gizlenmişse `hidden` `true` olur ve `article` `null` döner; arayüz haberin kaldırıldığını gösterir (FG-KO-03).

### 5.2 Kaydedilmiş aramalar (FG-KO-04)

| Yöntem ve adres | Açıklama | Yanıt |
|---|---|---|
| `GET /api/v1/me/saved-searches` | Kullanıcının kaydedilmiş aramaları | 200 |
| `POST /api/v1/me/saved-searches` | Yeni arama kaydeder | 201 |
| `PUT /api/v1/me/saved-searches/{id}` | Aramayı bütünüyle değiştirir | 200 |
| `DELETE /api/v1/me/saved-searches/{id}` | Aramayı siler | 204 |

```json
{
  "name": "Ekonomi haberleri",
  "query": "faiz",
  "filters": {
    "sources": ["TRT", "NTV"],
    "language": "tr",
    "categories": ["ECONOMY"],
    "lastDays": 7,
    "sort": "newest"
  }
}
```

- Tarih filtresi yalnızca göreli olarak (`lastDays`) saklanır.
- Bir kullanıcı aynı adla iki arama kaydedemez (`409 ALREADY_EXISTS`).
- Kullanıcılar yalnızca kendi aramalarına erişebilir; başka bir kullanıcının aramasına yapılan istek `404` döner.

## 6. Yönetim

### 6.1 Kullanıcılar

| Yöntem ve adres | Açıklama | Yanıt |
|---|---|---|
| `GET /api/v1/admin/users` | `status`, `role` ve `q` (e-posta veya adda arama) filtreleriyle sayfalı liste (FG-YP-01) | 200 |
| `POST /api/v1/admin/users/{id}/approve` | Yalnızca `PENDING` kullanıcıyı `ACTIVE` yapar; rolü `USER` olur | 200 |
| `POST /api/v1/admin/users/{id}/reject` | Yalnızca `PENDING` kullanıcıyı `REJECTED` yapar | 200 |
| `PATCH /api/v1/admin/users/{id}` | `role` (`USER`, `ADMIN`) ve `status` (`ACTIVE`, `PASSIVE`) değiştirir (FG-YP-02) | 200 |

- Durumuna uymayan onay veya ret isteği `409 INVALID_STATE_TRANSITION` döner.
- Sistemde aktif yönetici kalmamasına yol açacak bir değişiklik `409 LAST_ACTIVE_ADMIN` ile reddedilir (FG-YP-03). Bu kural, yöneticinin kendi rolünü veya durumunu değiştirmesi için de geçerlidir.
- Durumu `PASSIVE` yapılan kullanıcının erişimi bir sonraki isteğinde kesilir (FOG-19).

### 6.2 Kaynaklar

| Yöntem ve adres | Açıklama | Yanıt |
|---|---|---|
| `GET /api/v1/admin/sources` | Kaynakların sağlık özetiyle listesi: besleme sayısı, hatalı besleme sayısı, son başarılı toplama (FG-YP-06) | 200 |
| `GET /api/v1/admin/sources/{id}` | Kaynağın ayrıntıları ve beslemelerinin sağlık durumları | 200 |
| `POST /api/v1/admin/sources` | Kaynak ekler (FG-YP-04) | 201 |
| `PATCH /api/v1/admin/sources/{id}` | Kaynağı düzenler veya devre dışı bırakır | 200 |
| `POST /api/v1/admin/sources/{id}/fetch` | Kaynağın etkin bütün beslemelerinin bir sonraki okuma zamanını şimdiye çeker (FG-YP-08). Kaynak devre dışıysa `409 INVALID_STATE_TRANSITION`. | 202 |
| `POST /api/v1/admin/sources/{id}/purge` | Kaynağın bütün içeriğinin silinmesini ister (FG-YP-14) | 202 |

- `code`, `readerType` ve `language` kaynak eklendikten sonra değiştirilemez: Değişmeleri, kaynağa ait mevcut haberlerle ve kategori eşlemeleriyle tutarsızlık oluşturur.
- **İçerik silme:** Kaynak önce devre dışı bırakılmış olmalıdır (`409 SOURCE_MUST_BE_DISABLED`); aksi halde silme sırasında yeni haberler eklenebilir. Geri alınamaz bir işlem olduğundan, istek gövdesi kaynağın kodunu onay olarak içermelidir (`{ "confirmationCode": "NYT" }`). Silme tamamlanana kadar kaynağın `purgeRequestedAt` alanı doludur.

### 6.3 Beslemeler

| Yöntem ve adres | Açıklama | Yanıt |
|---|---|---|
| `POST /api/v1/admin/sources/{id}/feeds` | Kaynağa besleme ekler (FG-YP-04). Besleme ilk olarak hemen okunur. | 201 |
| `PATCH /api/v1/admin/feeds/{id}` | Beslemeyi düzenler veya devre dışı bırakır | 200 |

- Varsayılan kategori, kategori koduyla verilir (`defaultCategoryCode`).
- Otomatik olarak devre dışı kalmış (`AUTO`) bir besleme yönetici tarafından yeniden etkinleştirildiğinde, art arda hata sayısı sıfırlanır ve besleme hemen okunur.

### 6.4 Besleme testi (FG-YP-13)

| Yöntem ve adres | Açıklama | Yanıt |
|---|---|---|
| `POST /api/v1/admin/feed-tests` | Bir besleme adresinin, kayıtlı bir kaynağın ayarlarıyla test edilmesini ister: `{ "sourceId": "...", "url": "..." }` | 202 |
| `GET /api/v1/admin/feed-tests/{id}` | Testin durumunu ve sonucunu döner | 200 |

- Test işçi tarafından yapılır; okunan haberler kaydedilmez. Arayüz sonucu birkaç saniyede bir sorar.
- Yeni bir kaynağın beslemeleri test edilecekse kaynak önce devre dışı olarak eklenir.
- Sonuç örneği:

```json
{
  "id": "...",
  "status": "SUCCEEDED",
  "httpStatus": 200,
  "itemsFound": 35,
  "sampleItem": {
    "title": "...",
    "url": "https://...",
    "publishedAt": "2026-11-05T08:00:00Z",
    "categories": ["SPORTS"],
    "imageSourceUrl": "https://..."
  },
  "error": null
}
```

`status`: `PENDING`, `SUCCEEDED` veya `FAILED`.

### 6.5 Toplama geçmişi

`GET /api/v1/admin/ingestion-runs`: `sourceId`, `feedId`, `status`, `from` ve `to` filtreleriyle, en yeniden eskiye sayfalı liste (FG-YP-05).

### 6.6 Haber yönetimi

| Yöntem ve adres | Açıklama | Yanıt |
|---|---|---|
| `GET /api/v1/admin/articles` | `hidden`, `sources`, `from` ve `to` filtreleriyle sayfalı haber listesi. Gizlenen haberler aramada bulunmadığından, gizlemeyi geri almak için bu liste kullanılır. | 200 |
| `POST /api/v1/admin/articles/{id}/hide` | Haberi gizler (FG-YP-09); gövde `{ "reason": "..." }`, gerekçe zorunludur | 200 |
| `POST /api/v1/admin/articles/{id}/unhide` | Gizlemeyi geri alır | 200 |

Zaten gizli bir haberi gizleme veya gizli olmayan bir haberin gizlemesini geri alma isteği `409 INVALID_STATE_TRANSITION` döner.

### 6.7 İstatistikler

`GET /api/v1/admin/stats` (FG-YP-12):

```json
{
  "articles": {
    "total": 125000,
    "last24h": 2400,
    "bySource": [{ "code": "TRT", "total": 40000, "last24h": 800 }]
  },
  "users": { "PENDING": 2, "ACTIVE": 15, "PASSIVE": 1, "REJECTED": 0 },
  "feeds": { "enabled": 120, "failing": 3, "disabledAuto": 1 },
  "searchIndex": { "pendingOutboxEvents": 0 },
  "components": {
    "database": "UP",
    "elasticsearch": "UP",
    "objectStorage": "UP",
    "workerLastActivityAt": "2026-11-05T10:14:00Z"
  }
}
```

- `workerLastActivityAt`: İşçinin son toplama kaydının zamanı. İki uygulama yalnızca veri depoları üzerinden iletişim kurduğundan (ADR-0017), işçinin canlı olup olmadığı buradan anlaşılır.
- `pendingOutboxEvents`: Elasticsearch'e henüz aktarılmamış değişiklik sayısı. Sürekli artması, aktarımda bir sorun olduğunu gösterir.

### 6.8 Audit kayıtları

| Yöntem ve adres | Açıklama | Yanıt |
|---|---|---|
| `GET /api/v1/admin/audit-events` | `actorUserId`, `action`, `targetType`, `targetId`, `result`, `from` ve `to` filtreleriyle sayfalı liste (FG-YP-10). Tarih aralığı verilmezse son 30 gün. | 200 |
| `GET /api/v1/admin/audit-events/export` | Aynı filtrelerle CSV dosyası (`text/csv`) (FG-YP-11) | 200 |

- Dışa aktarma en fazla 100.000 kayıtla sınırlıdır; aşan istekler `400 EXPORT_TOO_LARGE` döner.
- CSV dosyası, Türkçe karakterlerin Excel'de doğru görünmesi için UTF-8 imza baytıyla (BOM) başlar.
- **CSV enjeksiyonuna karşı:** `=`, `+`, `-`, `@` ile başlayan değerlerin başına `'` karakteri eklenir. Aksi halde bu değerler dosya bir hesap tablosu programında açıldığında formül olarak çalıştırılabilir.
- Dışa aktarma işleminin kendisi de audit log'a kaydedilir.