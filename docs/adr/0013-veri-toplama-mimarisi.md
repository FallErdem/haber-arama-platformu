# ADR-0013: Veri Toplama Mimarisi

- **Durum:** Kabul edildi; toplama ADR-0017 ile Python işçisine taşındı
- **Tarih:** 2026-11-04

## Bağlam

Zamanlanmış işler, tek kopya çalışan toplayıcı rolünde yürütülmektedir (ADR-0005). Toplama işleminin şu gereksinimleri ve kısıtları karşılaması gerekir:

- Her beslemenin toplama sıklığı ayrı tanımlanabilmeli ve yönetici tarafından değiştirilebilmelidir (FG-VT-03).
- Yönetici, zamanlanmış toplamayı beklemeden bir kaynak için toplamayı elle başlatabilmelidir (FG-YP-08). Bu istek API rolünden toplayıcı rolüne iletilmelidir.
- Kaynakların istek kurallarına uyulmalıdır: robots.txt kuralları, Global Voices için 10 saniyelik `Crawl-delay`, NYT API için istekler arasında 12 saniye ve günlük istek limitleri (FG-VT-05, FOG-05, ADR-0009).
- Bir kaynağın hatası diğer kaynakların toplanmasını etkilememelidir (FOG-08).
- Sistem kapalıyken kaçırılan toplamalar, sistem açıldığında telafi edilmelidir (R-11).
- Görseller kaynaktan indirilip MinIO'da saklanmalıdır (ADR-0010).

## Karar

### 1. Toplama akışı

Bir beslemenin toplanması şu adımlardan oluşur:

1. Beslemenin indirilmesi
2. RSS, Atom veya API yanıtının ayrıştırılması
3. Normalleştirme: tarihlerin UTC'ye çevrilmesi, kategori eşlemesinin uygulanması ve HTML içeriğin temizlenmesi
4. Tekrar kontrolü: Daha önce kaydedilmiş haberler görmezden gelinir (FG-VT-04)
5. Kaydetme: Haber kaydı, outbox kaydı (ADR-0012) ve görsel kuyruğu kaydı aynı işlem içinde yazılır

### 2. Zamanlama

- Her besleme kaydında bir sonraki okuma zamanı tutulur.
- Toplayıcı, birkaç saniyede bir okuma zamanı gelmiş beslemeleri sorgular ve okur. Okuma tamamlandığında bir sonraki okuma zamanı, beslemenin toplama sıklığına göre belirlenir.
- **Elle toplama:** API rolü, ilgili beslemelerin bir sonraki okuma zamanını şimdiki zaman olarak günceller; toplayıcı bu beslemeleri bir sonraki sorgulamada okur. Roller arası iletişim veritabanı üzerinden yapılır; ek bir mesajlaşma altyapısı gerekmez.
- Sistem açıldığında, okuma zamanı geçmiş beslemeler hemen okunur.

### 3. İstek kuralları

- Aynı kaynağın beslemeleri sırayla okunur; istekler arasında kaynak düzeyinde tanımlanan bekleme süresi uygulanır.
- Farklı kaynakların beslemeleri paralel okunabilir.
- Koşullu istek kullanılır: Önceki yanıtın `ETag` ve `Last-Modified` değerleri sonraki istekte gönderilir; besleme değişmemişse (`304 Not Modified`) içerik yeniden işlenmez.
- Her isteğin bir zaman aşımı vardır; en fazla 3 yönlendirme takip edilir.
- Toplayıcı, isteklerinde kendini kendi adıyla (`User-Agent`) tanıtır.
- Toplayıcı, kaynakların robots.txt kurallarına uyar.
- API anahtarı gibi gizli bilgiler içeren istek adresleri loglanmadan önce maskelenir (R-18).

### 4. Hata yönetimi

- Başarısız bir okuma, artan aralıklarla (1, 5 ve 15 dakika sonra) yeniden denenir.
- Art arda 5 başarısız okumadan sonra besleme otomatik olarak devre dışı kalır ve durum yönetim panelinde gösterilir (FG-YP-07).
- Bot koruması veya erişim engeli (örneğin HTTP 403) aşılmaya çalışılmaz; başarısız okuma olarak kaydedilir (FG-VT-06).
- İstek limiti aşıldığında (HTTP 429) beslemenin okunması ertelenir.
- Uygulama ayrıntıları (4. hatadaki süre, 429'da erteleme süresi, otomatik devre dışı bırakmanın audit kaydı) ADR-0017'nin 10. bölümündedir.

### 5. Görsel indirme

- Görseller, haberin kaydedilmesinden ayrı olarak, PostgreSQL'de tutulan bir görsel kuyruğu üzerinden indirilir. Böylece yavaş yanıt veren bir görsel sunucusu haberlerin toplanmasını yavaşlatmaz.
- Görsel kuyruğunu işleyen iş toplayıcı rolünde çalışır; görsel indirmeleri de istekler arası bekleme süresine tabidir.
- İndirilemeyen görseller belirli sayıda yeniden denenir; yine indirilemezse haberde yer tutucu gösterilir (FG-AR-08).

## Sonuçlar

- Toplamanın elle başlatılması, ek bir altyapı bileşeni olmadan veritabanı üzerinden yapılır. Elle başlatılan toplama, toplayıcının bir sonraki sorgulamasına kadar (birkaç saniye) gecikir.
- Besleme kaydı; bir sonraki okuma zamanı, son `ETag` ve `Last-Modified` değerleri, art arda başarısız okuma sayısı ve son başarılı okuma zamanı gibi alanları içerecektir.
- Görsel kuyruğu için PostgreSQL'de ayrı bir tablo gerekecektir.
- Koşullu istekler, kaynak sitelere yapılan yükü ve gereksiz işlemeyi azaltır.