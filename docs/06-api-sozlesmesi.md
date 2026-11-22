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

- Sayfalanmayan listeler de öğelerini doğrudan bir dizi olarak değil, `items` alanında döndürür (`{ "items": [] }`); arayüz bütün listeleri aynı biçimde okur ve yanıta sonradan alan eklenebilir.
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

- `type` alanı, değeri `about:blank` olduğunda yanıtta gönderilmez; RFC 9457'ye göre alanın bulunmaması aynı anlama gelir.
- `errors` alanı yalnızca girdi doğrulama hatalarında bulunur. Geçersiz alanların hepsi birlikte bildirilir. Alan kodları: `INVALID_VALUE` (biçim yanlış veya izin verilen değerlerden biri değil), `MIN_VALUE`, `MAX_VALUE`, `MAX_LENGTH`, `INVALID_RANGE` (aralığın başlangıcı bitişinden sonra).
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
| 503 | `MEDIA_UNAVAILABLE` | Görselin bulunduğu nesne depolamaya (MinIO) ulaşılamıyor |
| 503 | `SEARCH_UNAVAILABLE` | Arama indeksine (Elasticsearch) ulaşılamıyor; arama ve haber detayı (metinler indekstedir) kullanılamaz, diğer uç noktalar çalışmaya devam eder (FOG-09) |
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
| `from`, `to` | Yayın tarihi aralığı, sınırlar dahil; ISO 8601 ve UTC (örnek: `2026-11-05T00:00:00Z`). `from`, `to`'dan sonra olamaz |
| `sort` | `relevance` (ilgililik) veya `newest` (en yeni). `q` doluysa varsayılan `relevance`, boşsa `newest`; `q` boşken `relevance` yok sayılır. |
| `page`, `size` | Bkz. 2.4 |

- Arama ifadesi başlıkta, özette ve tam metinde aranır; başlıktaki eşleşme en yüksek, tam metindeki en düşük ağırlığı alır (FG-AR-01). Bir veya iki kelimelik ifadede kelimelerin hepsi, daha uzun ifadede dörtte üçü geçmelidir; kelimeler farklı alanlarda olabilir. Türkçe karaktersiz yazılan ifade de (örnek: `cumhurbaskani`) eşleşir. Kelimeleri yan yana ve aynı sırada içeren haber üstte çıkar. Tırnak içinde yazılan öbek (örnek: `"merkez bankası" faiz`) zorunludur: yalnızca öbeği kelimeleri yan yana ve aynı sırada içeren haberler döner. Sorgunun kuralları ve gerekçeleri: `05-veri-modeli.md`, 5.5.
- Birden fazla kaynak veya kategori verildiğinde, herhangi birini taşıyan haberler döner; farklı filtreler birlikte uygulanır.
- Kategori filtresinde `BREAKING` (Son Dakika) seçiliyse, yalnızca son 6 saatte yayımlanan haberler döner (FG-AR-12). Süresi dolan haber konu kategorilerinde görünmeye devam eder; yanıttaki `categories` alanında `BREAKING` yer almaz. Süre `categories.window_hours` sütunundan okunur.
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
  "otherSourcesCount": 2,
  "saved": false
}
```

- `highlights`: Eşleşen kelimeler `<mark>` etiketiyle işaretlenir (FG-AR-05). Metnin geri kalanı backend'de HTML kaçış karakterleriyle güvenli hale getirilir; arayüz `<mark>` dışındaki hiçbir etiketi işlemez. `q` boşsa bu alan bulunmaz.
- Vurgular yalnızca başlık ve özet için döner; alanın tamamı döner, parçalara bölünmez. Eşleşme yalnızca tam metindeyse `highlights` boş bir nesnedir.
- `image`: Haberin ana görseli: indirilmiş görsellerinden sırası en küçük olanı (ana görsel indirilemediyse sıradaki). `url` imzalı görsel adresidir (bkz. 4.4). Görsel yoksa veya henüz indirilmemişse `null`, arayüz yer tutucu gösterir (FG-AR-08).
- `otherSourcesCount`: Aynı gruptaki diğer kaynakların sayısı.
- `saved`: Haberin isteği yapan kullanıcı tarafından kaydedilip kaydedilmediği (FG-KO-01); arayüz sonuçtan kaydetmeyi buna göre sunar. Bir sayfanın bütün sonuçları için tek sorguyla bulunur.
- Yanıtın sayfalama alanlarına ek olarak `totalRelation` alanı bulunur (bkz. 2.4).
- Başlık, kaynak, adres, kategoriler ve görsel asıl kayıttan (PostgreSQL), özet arama indeksinden okunur (ADR-0019). Gizlenmiş haberin belgesi indekste gizli olarak işaretlidir; sonuçta yer almaz ve toplam sayıya girmez. PostgreSQL'de gizlenmiş veya silinmiş ama indeksteki belgesi henüz güncellenmemiş bir haber de sonuçta yer almaz (FG-AR-09); bu durumda bir sayfa `size` değerinden az öğe taşıyabilir.
- Arama indeksine ulaşılamıyorsa `503 SEARCH_UNAVAILABLE` döner.

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

- `summary`, `content` ve `author` arama indeksinden (Elasticsearch), diğer alanlar asıl kayıttan (PostgreSQL) okunur (ADR-0019). Haber yeni kaydedildiyse ve indekse henüz aktarılmadıysa (birkaç saniye) bu üç alan `null`'dır.
- `content`: Tam metin; işçi tarafından temizlenmiş HTML (FOG-16). Kaynak tam metin vermiyorsa `null`, arayüz özeti gösterir (FG-AR-06).
- `author`: Kaynak yazar bilgisi vermiyorsa `null`.
- `media`: Yalnızca indirilmiş görseller, haberdeki sırasıyla listelenir; `url` imzalı görsel adresidir (bkz. 4.4). Görseli olmayan haberde boş listedir; arayüz yer tutucu gösterir (FG-AR-08). Mevcut kaynaklar altyazı ve fotoğrafçı bilgisi vermediğinden `caption` ve `credit` şimdilik `null`'dır.
- `categories`: Arama sonuçlarındaki kuralla aynıdır; süresi dolan haberde `BREAKING` yer almaz (bkz. 4.1).
- `otherSources`: Kaynaklar arası gruplama (FG-AR-10) gelene kadar boş listedir.
- `saved`: Haberin isteği yapan kullanıcı tarafından kaydedilip kaydedilmediği (FG-KO-01).
- Arayüz, kaynağın koduna göre gerekli atıfı ve logoyu gösterir (FG-AR-07, ADR-0009).
- Gizlenmiş veya kayıtlı olmayan bir haber için `404 NOT_FOUND`, kimlik geçerli bir UUID değilse `400 VALIDATION_FAILED`, arama indeksine ulaşılamıyorsa `503 SEARCH_UNAVAILABLE` döner.

### 4.3 `GET /api/v1/sources` ve `GET /api/v1/categories`

Arama filtreleri için etkin kaynakların (`code`, `name`, `language`) ve kategorilerin (`code`, `kind`, `sortOrder`) listesini döner.

- Kaynaklar ada göre, kategoriler arayüzde gösterilecekleri sıraya (`sortOrder`) göre sıralıdır. Devre dışı bırakılan kaynak listede yer almaz.
- Kategorinin görünen adı yanıtta yoktur; arayüz adı kendi dil dosyalarından koda göre bulur (FOG-31). `kind`: `TOPIC` (konu) veya `TEMPORAL` (Son Dakika).
- Listeler sayfalanmaz; yanıt, sayfalı listelerde olduğu gibi öğeleri `items` alanında taşır (bkz. 2.4):

```json
{
  "items": [
    { "code": "CNNTURK", "name": "CNN Türk", "language": "tr" },
    { "code": "GLOBALVOICES", "name": "Global Voices", "language": "en" }
  ]
}
```

### 4.4 `GET /api/v1/media/{id}` — Görsel

Görselin kendisini döner. HTML'deki `<img>` etiketi istek başlığı ekleyemediğinden bu uç nokta JWT değil, imzalı adres ister.

- **Adres biçimi:** `/api/v1/media/{id}?exp={son geçerlilik zamanı}&sig={imza}`. Adresler yalnızca API yanıtlarında üretilir.
- **İmza:** `id` ve `exp` değerlerinin, API'nin yapılandırmasındaki gizli bir anahtarla hesaplanan HMAC-SHA256 değeri. Anahtar bütün API kopyalarında aynıdır ve bir gizli bilgi olarak yönetilir (R-16).
  - İmzalanan metin `{id}.{exp}`'dir; `exp`, Unix zamanı (saniye) olarak yazılır. Sonuç adreste kullanılabilen, dolgusuz Base64 biçimindedir (RFC 4648, 5. bölüm).
  - Anahtar en az 32 karakterdir (`MEDIA_SIGNING_KEY`); eksik veya kısaysa API açılmaz.
  - İmzalar sabit sürede karşılaştırılır; yanıt süresinden imzanın ne kadarının doğru olduğu çıkarılamaz.
- **Geçerlilik süresi:** `exp`, üretildiği saatin başlangıcından 2 saat sonradır. Böylece adres 1 ile 2 saat arasında geçerli kalır ve aynı saat içinde üretilen bütün yanıtlarda bir görselin adresi aynı olur; tarayıcı görseli önbellekten kullanabilir.
- **Kontroller:** İmza geçersizse, süre dolmuşsa veya `exp`/`sig` eksikse `403 MEDIA_URL_INVALID` döner. İmza veritabanına bakılmadan önce denetlenir; imzasız bir istek görselin var olup olmadığını öğrenemez. Görsel indirilmemişse, dosyası bulunamıyorsa veya ait olduğu haber gizlenmişse `404 NOT_FOUND`, nesne depolamaya ulaşılamıyorsa `503 MEDIA_UNAVAILABLE` döner.
- Uç nokta yalnızca `GET` ile açıktır; aynı adres yapısındaki başka istekler token ister.
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

- Kullanıcı token'dan belirlenir; adreste kullanıcı kimliği yoktur ve her sorgu kullanıcıya göre süzülür. Bir kullanıcının başka birinin kayıtlarını görmesinin veya değiştirmesinin yolu yoktur.
- Liste `page` ve `size` parametrelerini alır (bkz. 2.4). Aynı anda kaydedilen haberlerin sırası haber kimliğiyle sabitlenir; sayfalar arasında bir haber iki kez görünmez veya kaybolmaz.
- `PUT` tekrarlanabilir: aynı istek ikinci kez gelirse kayıt ve kaydedilme zamanı (`savedAt`) değişmez.
- Haberin başlığı, kaynağı ve görseli asıl kayıttan (PostgreSQL) okunur; listede özet yoktur. Gizlenmiş haber asıl kayıt sorgusunda dönmez; karşılığı gelmeyen kayıt gizlenmiş bir haberdir. Haberler silinmediğinden (kaynak içeriğinin silinmesi hariç; o zaman kayıtlar da silinir) başka bir nedeni yoktur.
- Kaydetme ve kayıttan çıkarma audit'e yazılmaz (FG-AL-01'deki işlemlerden değildir).

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

Listedeki her öğe ve işlemlerin yanıtı:

```json
{
  "id": "0193f1a2-...",
  "email": "kullanici@ornek.com",
  "displayName": "Erdem",
  "role": "USER",
  "status": "PENDING",
  "createdAt": "2026-11-05T10:00:00Z",
  "version": 0
}
```

- Liste kayıt zamanına göre yeniden eskiye sıralıdır. `q` en fazla 200 karakterdir; e-postada ve görünen adda, büyük/küçük harf ayrımı yapılmadan (Türkçe harfler dahil: `şahin` ile `ŞAHİN` eşleşir) aranır. `%` ve `_` joker değil, harfin kendisi olarak aranır.
- `PATCH` gövdesi: `role` ve `status` isteğe bağlıdır, verilmeyen değişmez; `version` zorunludur (bkz. 2.5). `status` yalnızca `ACTIVE` veya `PASSIVE` olabilir. Onay bekleyen veya reddedilmiş kullanıcının rolü ve durumu değiştirilemez (`409 INVALID_STATE_TRANSITION`); onların durumu onay ve ret işlemleriyle değişir. İstenen değerler zaten kayıttakiyse hiçbir şey değişmez.
- Onay, ret ve her değişiklik kullanıcının `version` değerini bir artırır.
- Rol ve durum değişiklikleri sırayla işlenir: iki yönetici aynı anda birbirinin rolünü düşürmeye çalışırsa ikinci istek birincinin sonucunu görür ve son yönetici kuralı yine uygulanır.
- Başarılı her işlem, işlemle aynı veritabanı işleminde audit log'a yazılır. İş kuralıyla reddedilen denemeler (`409`) de `FAILURE` sonucuyla ve ret nedeniyle yazılır; `404` ve `400` yanıtları yazılmaz (`05-veri-modeli.md`, 3.13).

### 6.2 Kaynaklar

| Yöntem ve adres | Açıklama | Yanıt |
|---|---|---|
| `GET /api/v1/admin/sources` | Kaynakların sağlık özetiyle listesi: besleme sayısı, hatalı besleme sayısı, son başarılı toplama (FG-YP-06) | 200 |
| `GET /api/v1/admin/sources/{id}` | Kaynağın ayrıntıları ve beslemelerinin sağlık durumları | 200 |
| `POST /api/v1/admin/sources` | Kaynak ekler (FG-YP-04) | 201 |
| `PATCH /api/v1/admin/sources/{id}` | Kaynağı düzenler veya devre dışı bırakır | 200 |
| `POST /api/v1/admin/sources/{id}/fetch` | Kaynağın etkin bütün beslemelerinin bir sonraki okuma zamanını şimdiye çeker (FG-YP-08). Kaynak devre dışıysa `409 INVALID_STATE_TRANSITION`. | 202 |
| `POST /api/v1/admin/sources/{id}/purge` | Kaynağın bütün içeriğinin silinmesini ister (FG-YP-14) | 202 |

- `code`, `readerType` ve `language` kaynak eklendikten sonra değiştirilemez: Değişmeleri, kaynağa ait mevcut haberlerle ve kategori eşlemeleriyle tutarsızlık oluşturur. `PATCH` gövdesinde bulunurlarsa istek `400 VALIDATION_FAILED` ile reddedilir.
- **Liste** (`GET /admin/sources`) sayfalanmaz, ada göre sıralıdır; her öğe: `id`, `code`, `name`, `readerType`, `language`, `enabled`, `feedCount`, `failingFeedCount`, `lastSuccessAt`, `purgeRequestedAt`. Hatalı besleme: etkin olup son okuması başarısız olan (`consecutiveFailures > 0`) ya da kendiliğinden kapanmış (`AUTO`) besleme; elle kapatılmış beslemenin eski hataları sayılmaz.
- **Detay** (`GET`, `POST` ve `PATCH` yanıtı): kaynağın bütün ayarları (`homepageUrl`, `requestIntervalSeconds`, `dailyRequestLimit`, `license`, `attributionText`, `feedTimeZone`), `enabled`, `purgeRequestedAt`, `version`, `articleCount` (kaynağın gizlenenler dahil haber sayısı) ve ada göre sıralı `feeds` (bkz. 6.3).
- **Ekleme** gövdesi: `code` (büyük harfle başlar; büyük harf, rakam ve alt çizgi, en fazla 40 karakter), `name`, `homepageUrl` (`http` veya `https`), `readerType`, `language` (`tr`, `en`), `requestIntervalSeconds` (1–3600); isteğe bağlı `dailyRequestLimit`, `license`, `attributionText`, `feedTimeZone` (IANA saat dilimi adı, örnek `Europe/Istanbul`). Kaynak devre dışı eklenir. `readerType` şimdilik `RSS` veya `ATOM`'dur; NYT okuyucusu İ-13 ile eklenecek. Kod veya ad başka bir kaynakta varsa `409 ALREADY_EXISTS`.
- **Düzenleme:** Gövdede bulunmayan alan değişmez; boş bırakılabilen bir alana (`dailyRequestLimit`, `license`, `attributionText`, `feedTimeZone`) `null` gönderilirse alan boşaltılır. `enabled` ile kaynak etkinleştirilir veya devre dışı bırakılır.
- **Elle toplama** yanıtı: `{ "feedCount": 2 }`, okunacak etkin besleme sayısı. Okumayı işçi bir sonraki turunda (en fazla 30 saniye içinde) yapar ve `MANUAL` olarak kaydeder.
- **İçerik silme:** Kaynak önce devre dışı bırakılmış olmalıdır (`409 SOURCE_MUST_BE_DISABLED`); aksi halde silme sırasında yeni haberler eklenebilir. Geri alınamaz bir işlem olduğundan, istek gövdesi kaynağın kodunu onay olarak içermelidir (`{ "confirmationCode": "NYT" }`); kod yoksa veya kaynağın kodu değilse `400 VALIDATION_FAILED`. Yanıt: `{ "articleCount": 1240 }`, silinecek haber sayısı. Silmeyi işçi parça parça yapar (`05-veri-modeli.md` 4. bölüm); silme tamamlanana kadar kaynağın `purgeRequestedAt` alanı doludur. Bu sürede yeniden silme istenemez ve kaynak etkinleştirilemez (`409 INVALID_STATE_TRANSITION`).

### 6.3 Beslemeler

| Yöntem ve adres | Açıklama | Yanıt |
|---|---|---|
| `POST /api/v1/admin/sources/{id}/feeds` | Kaynağa besleme ekler (FG-YP-04). Besleme ilk olarak hemen okunur. | 201 |
| `PATCH /api/v1/admin/feeds/{id}` | Beslemeyi düzenler veya devre dışı bırakır | 200 |

- Varsayılan kategori, kategori koduyla verilir (`defaultCategoryCode`); tanınmayan kod `400 VALIDATION_FAILED` alır. Karışık içerikli beslemede `null`'dır.
- Otomatik olarak devre dışı kalmış (`AUTO`) bir besleme yönetici tarafından yeniden etkinleştirildiğinde, art arda hata sayısı sıfırlanır ve besleme hemen okunur. Elle kapatılmış (`MANUAL`) besleme etkinleştirildiğinde de hemen okunur. Yöneticinin kapattığı beslemenin nedeni `MANUAL` olur.
- **Besleme** (`POST` ve `PATCH` yanıtı, kaynak detayındaki `feeds` öğeleri): `id`, `sourceId`, `name`, `url`, `defaultCategoryCode`, `useItemCategories`, `fetchIntervalMinutes`, `enabled`, `disabledReason` (`MANUAL`, `AUTO`), `consecutiveFailures`, `lastSuccessAt`, `lastError`, `nextFetchAt`, `manualFetchRequestedAt`, `version`.
- **Ekleme** gövdesi: `name`, `url` (`http` veya `https`), `useItemCategories`, `fetchIntervalMinutes` (1–1440); isteğe bağlı `defaultCategoryCode`. Besleme etkin eklenir. Adres başka bir beslemede veya ad aynı kaynağın başka bir beslemesinde varsa `409 ALREADY_EXISTS`.
- **Düzenleme:** Gövdede bulunmayan alan değişmez; `defaultCategoryCode`'a `null` gönderilirse boşaltılır. Adres değişirse eski adresin koşullu istek değerleri (ETag, Last-Modified) silinir.
- Kaynak ve besleme düzenlemelerinde `version` zorunludur (bkz. 2.5). `version` yalnızca yöneticinin değişikliklerinde artar; işçinin yazdığı sağlık alanları (hata sayısı, son okuma, otomatik kapanma) sürümü değiştirmez.
- Kaynak ve besleme işlemleri, başarılı olsun olmasın, audit log'a yazılır; iş kuralıyla reddedilen denemeler (`409`) `FAILURE` sonucuyla ve ret nedeniyle yazılır (`05-veri-modeli.md`, 3.13).

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

- `status`: `RUNNING`, `SUCCEEDED`, `NOT_MODIFIED`, `FAILED`. `from` ve `to` okumanın başlangıç zamanına uygulanır (ISO 8601, UTC; sınırlar dahil).
- Her öğe: `id`, `feedId`, `feedName`, `sourceId`, `sourceCode`, `sourceName`, `trigger` (`SCHEDULED`, `MANUAL`), `status`, `startedAt`, `finishedAt`, `httpStatus`, `itemsReceived`, `itemsNew`, `itemsDuplicate`, `itemsFailed`, `errorMessage`. Haber sayıları başarısız okumada `null`'dır.

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
    "bySource": [{ "code": "TRT", "name": "TRT Haber", "total": 40000, "last24h": 800 }]
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

- `articles`: Gizlenen haberler de sayılır. `last24h`, son 24 saatte toplanan haberlerdir. `bySource` bütün kaynakları ada göre verir; haberi olmayan kaynak 0 ile yer alır.
- `users`: Durumlara göre kullanıcı sayıları; hiç kullanıcısı olmayan durum 0 ile yer alır.
- `feeds`: `enabled` okunan beslemeler (kendisi ve kaynağı etkin), `failing` bunlardan son okuması başarısız olanlar, `disabledAuto` art arda hatalar yüzünden kendiliğinden kapananlar.
- `components`: Her bileşen `UP` veya `DOWN`.
  - `database`: Sayılar veritabanından geldiği için yanıt dönüyorsa `UP`'tır.
  - `elasticsearch`: Elasticsearch yanıt veriyor ve arama yapılabiliyorsa (kümenin durumu yeşil veya sarı) `UP`, kırmızıysa veya yanıt vermiyorsa `DOWN`.
  - `objectStorage`: Var olmayan bir dosya istenir. MinIO "dosya yok" veya "erişim yok" diye yanıt verirse ayaktadır (`UP`); hiç yanıt vermezse `DOWN`. Bu kontrol için API'ye yeni yetki verilmez.
  - Elasticsearch veya MinIO kapalı olsa da pano açılır ve onları `DOWN` gösterir (FOG-09).
- `workerLastActivityAt`: İşçinin en son başlattığı toplamanın zamanı; hiç toplama yoksa `null`. İki uygulama yalnızca veri depoları üzerinden iletişim kurduğundan (ADR-0017), işçinin çalışıp çalışmadığı buradan anlaşılır.
- `pendingOutboxEvents`: Elasticsearch'e henüz aktarılmamış değişiklik sayısı. Sürekli artması, aktarımda bir sorun olduğunu gösterir.

### 6.8 Audit kayıtları

| Yöntem ve adres | Açıklama | Yanıt |
|---|---|---|
| `GET /api/v1/admin/audit-events` | `actorUserId`, `action`, `targetType`, `targetId`, `result`, `from` ve `to` filtreleriyle sayfalı liste (FG-YP-10). Tarih aralığı verilmezse son 30 gün. | 200 |
| `GET /api/v1/admin/audit-events/export` | Aynı filtrelerle CSV dosyası (`text/csv`) (FG-YP-11) | 200 |

- **Filtreler:** `actorUserId` ve `targetId` UUID; `action` işlem kodu `targetType` `USER`, `SOURCE` veya `FEED`; `result` `SUCCESS` veya `FAILURE`; `from` ve `to` ISO 8601 zaman (ikisi de dahil). Tarih aralığı verilmezse son 30 gün; yalnızca `to` verilirse ondan önceki 30 gün.
- Liste zamana göre yeniden eskiye sıralıdır. Öğenin alanları: `id`, `occurredAt`, `actorType` (`USER`, `SYSTEM`), `actorUserId`, `actorEmail`, `action`, `targetType`, `targetId`, `result`, `requestId`, `ipAddress`, `details` (işleme özgü alanlar; yoksa boş nesne). Sistem kayıtlarında kullanıcı, istek kimliği ve IP adresi `null`'dır.
- Dışa aktarma en fazla 100.000 kayıtla sınırlıdır; aşan istekler `400 EXPORT_TOO_LARGE` döner. Üst sınır dışa aktarmanın başladığı ana sabitlenir; dışa aktarma sürerken yazılan kayıtlar (dışa aktarmanın kendi kaydı dahil) dosyaya girmez.
- CSV sütunları: `id`, `occurred_at`, `actor_type`, `actor_user_id`, `actor_email`, `action`, `target_type`, `target_id`, `result`, `request_id`, `ip_address`, `details` (JSON metni). Zamanlar UTC'dir.
- CSV dosyası, Türkçe karakterlerin Excel'de doğru görünmesi için UTF-8 imza baytıyla (BOM) başlar.
- **CSV enjeksiyonuna karşı:** `=`, `+`, `-`, `@`, sekme, satır başı veya satır sonu karakteriyle ya da `＝`, `＋`, `－`, `＠` (bazı dillerde formül başlatan tam genişlikli karşılıklar) ile başlayan değerlerin başına `'` karakteri eklenir (OWASP "CSV Injection" listesi). Aksi halde bu değerler dosya bir hesap tablosu programında açıldığında formül olarak çalıştırılabilir. Kayıtlarda dışarıdan gelen değerler bulunur: kullanıcının seçtiği e-posta, besleme adı, kaynak sitenin hata metni.
- Dışa aktarma işleminin kendisi de audit log'a kaydedilir (`AUDIT_EXPORTED`; veri modeli 3.13). Sınırı aşan istek bir doğrulama hatasıdır ve kaydedilmez.