# Haber Kaynakları Araştırması

- **Araştırma tarihi:** 2 Kasım 2026
- **İlgili kararlar:** ADR-0003, ADR-0004, ADR-0006, ADR-0009, ADR-0010

> Kullanım şartları, lisanslar ve beslemeler zamanla değişebilir. Bu dokümandaki bulgular araştırma tarihindeki durumu yansıtır.

## 1. Amaç ve Değerlendirme Kriterleri

Bu araştırmanın amacı, uygulamanın haber toplayacağı kaynakları belirlemektir. Şartname; birden fazla ve farklı türde kaynaktan düzenli veri toplanmasını, kaynakların kullanım şartlarına ve erişim kurallarına uyulmasını, giriş, ödeme duvarı veya bot korumasının aşılmamasını ve kaynak sitelere aşırı yük bindirilmemesini istemektedir.

Her aday kaynak aşağıdaki kriterlere göre değerlendirilmiştir:

| Kriter | Soru |
|---|---|
| Erişim türü | RSS/Atom beslemesi mi, resmi API mi? |
| Kullanım hakkı | Kullanım şartları veya içerik lisansı, haberlerin toplanmasına, saklanmasına ve kurum içi kullanıcılara gösterilmesine izin veriyor mu? |
| Erişim kuralları | robots.txt, besleme adresini kapsayan bir kısıtlama veya istek aralığı (Crawl-delay) içeriyor mu? |
| Teknik erişilebilirlik | Otomatik isteklere yanıt veriyor mu, yoksa bot koruması veya erişim engeli var mı? |
| Güncellik | Düzenli olarak yeni içerik yayınlanıyor mu? |
| Gelen alanlar | Başlık, özet, tam metin, görsel, tarih, yazar, kategori ve benzersiz kimlik geliyor mu? |
| Dil | Türkçe mi, İngilizce mi? |

Kullanım hakkı kriteri belirleyici kabul edilmiştir: Teknik olarak ne kadar uygun olursa olsun, kullanım hakkı açık olmayan bir kaynak seçilmemiştir. Bu kuralın tek istisnası, şirket kararıyla ADR-0004 kapsamında kaynak setine alınan Türk haber kaynaklarıdır.

## 2. Kaynak Türleri

| Tür | Tanım | Güçlü yönler | Zayıf yönler |
|---|---|---|---|
| RSS / Atom | Yayıncının içeriğini başka uygulamaların okuması için yayınladığı XML beslemesi | Yayıncının sunduğu resmi kanal; anahtar gerektirmez | Format kaynaktan kaynağa farklılık gösterir; çoğunlukla yalnızca özet içerir; beslemenin yayınlanması tek başına içeriğin kullanım hakkını vermez |
| Resmi API | Yayıncının geliştiricilere kayıt ve anahtarla sunduğu programatik erişim | Yapılandırılmış ve tutarlı veri; kullanım koşulları açıkça tanımlıdır | İstek limitleri ve saklama kısıtları olabilir |
| Sayfa kazıma (scraping) | Haber sayfalarının HTML içeriğinin indirilip ayrıştırılması | RSS veya API sunmayan sitelere erişim sağlar | Site tasarımı değiştiğinde bozulur; çoğu kullanım şartında yasaktır; bot korumalarıyla karşılaşma olasılığı yüksektir |

Sayfa kazıma bu projede kullanılmamaktadır. Gerekçeleri: kullanım şartlarıyla çelişme riskinin yüksek olması, şartnamenin bot korumasının aşılmaması kuralıyla çatışabilmesi ve bakım maliyetinin yüksek olması.

Aynı gerekçelerle iki tür kaynak daha kullanılmamaktadır: yayıncının kendi alan adında sunulmayan üçüncü taraf beslemeler ve başka yayıncıların içeriğini yeniden dağıtan haber toplayıcı servisler. Bu kaynaklar kullanıldığında, içeriğin özgün yayıncısının kullanım şartları hiç görülmeden kullanılmış olur.

## 3. İncelenen Kaynaklar

Sonuç değerleri:

- **Seçildi:** Başlangıç kaynak setine alındı.
- **İleride eklenebilir:** Kullanım hakkı doğrulandı, başlangıç setine alınmadı.
- **Elendi:** Kriterleri karşılamıyor.

### 3.1 Türkçe Kaynaklar

| Kaynak | Tür | Sonuç | Gerekçe |
|---|---|---|---|
| TRT Haber | RSS | Elendi | robots.txt besleme adresine izin veriyor. Ancak kullanım koşulları (son güncelleme 28.04.2021) içeriğin herhangi bir mecrada kopyalanmasını ve kullanılmasını (md. 1.2); materyallerin bireysel amaçlar dışında kullanılmasını, üçüncü kişilere devredilmesini ve arşiv yapılarak kullandırılmasını (md. 5.2) yasaklıyor. |
| NTV | Atom | Elendi | robots.txt besleme adresine izin veriyor. Ancak kullanım koşulları (md. 14) içeriğin yazılı izin olmadan kullanılmasını, çoğaltılmasını ve başka bir bilgisayara yüklenmesini yasaklıyor. |
| CNN Türk | RSS | Elendi | robots.txt besleme adresine (`/feed/`) izin veriyor. Ancak yasal uyarı yalnızca kişisel ve ticari olmayan kullanım için indirmeye izin veriyor; kopyalamayı, çoğaltmayı ve başka bir bilgisayara yüklemeyi yasaklıyor. Kullanım şartları da materyallerin bireysel amaçlar dışında kullanılamayacağını belirtiyor. |
| Habertürk | RSS | Elendi | Kullanım koşulları içeriğin bot, tarayıcı (crawler/scraper) veya benzeri yöntemlerle toplu olarak çekilmesini ve veri madenciliğine tabi tutulmasını yazılı izin olmadan açıkça yasaklıyor (md. 8). İçeriğin bireysel amaçlar dışında kullanılması ve arşivlenerek çoğaltılması da yasak (md. 6). |
| Anadolu Ajansı | RSS, API | Elendi | API yalnızca abonelik sözleşmesiyle, kullanıcı adı ve parolayla erişilebiliyor (ödeme duvarı). RSS beslemesinde lisans bilgisi yok; kullanım koşulları sayfası bulunamadı. AA, web sitesindeki haberlerin abonelere sunulan haberlerin özeti olduğunu belirtiyor. Açık bir izin bulunmadığından içerik korunmaya devam eder. |
| BBC Türkçe | RSS | Elendi | BBC Türkçe'nin kendi kullanım koşulları (yayın 21.07.2009, güncelleme 16.04.2010), içeriğin ticari amaçlı olmayan kişisel kullanım dışında kopyalanmasını, indirilmesini, bir siteye konmasını ve kamuya sunulmasını yasaklıyor; bu tür kullanımları önceden yazılı izne bağlıyor (md. 4). Beslemenin telif alanı ise BBC'nin genel kullanım koşullarına yönlendiriyor; iki metin aynı yönde. |
| Bianet | RSS | Elendi | Sitenin kendi sayfalarında "all rights reserved" bildirimi var, açık lisans yok. Bir üçüncü taraf sitede görülen Creative Commons ibaresinin Bianet'e değil, o siteye ait olduğu tespit edildi. |
| VOA Türkçe | Besleme | Elendi | ABD kamu yayıncısı. Mart 2025'te yeni içerik yayını durdu, Mart 2026'da mahkeme yayınların yeniden başlatılmasına hükmetti. Alan adı 2023'te RTÜK talebiyle Türkiye'den erişime engellendi; erişim engelinin aşılması proje kurallarına aykırı. |
| Global Voices Türkçe | RSS | Elendi | İçerik CC BY lisanslı, ancak beslemedeki son içerik 18.04.2021 tarihli. Düzenli veri toplama amacına uygun değil. |
| Teyit | RSS | Elendi | Otomatik isteğe HTTP 403 yanıtı veriyor (bot koruması). |
| Evrim Ağacı | RSS | Elendi | Telif bildirimi (©) var, açık lisans yok. |
| İklim Haber, Yeşil Gazete, NewsLab Turkey | RSS | Elendi | Ana sayfalarda açık lisans bildirimi bulunamadı. Lisans bildirimi olmayan içerik, telif hukuku gereği korunmaya devam eder. |

**Genel gözlem:** İncelenen ana akım Türk haber sitelerinin hepsi RSS beslemesi yayınlıyor, ancak kullanım koşulları içeriğin kopyalanmasını, saklanmasını veya başkalarına sunulmasını yazılı izne bağlıyor. Hiçbiri RSS beslemesinin kullanımına özel bir izin tanımlamıyor. Araştırma tarihinde, düzenli içerik yayınlayan ve açık lisans kullanan bir Türkçe haber kaynağı bulunamadı.
> **Not:** TRT Haber, NTV ve CNN Türk, 03.11.2026 tarihli şirket kararıyla ADR-0004 kapsamında kaynak setine alınmıştır. Bu tablodaki sonuçlar araştırma tarihindeki değerlendirmeyi yansıtır.

### 3.2 İngilizce Kaynaklar

| Kaynak | Tür | Sonuç | Gerekçe |
|---|---|---|---|
| The Guardian Open Platform | API | Seçildi, sonra çıkarıldı | Ücretsiz Developer anahtarı ticari olmayan kullanıma açık; tam metin veriyor. Kısıtları 4.1 bölümünde. 24 saat saklama kuralı nedeniyle ADR-0006 ile kaynak setinden çıkarıldı. |
| Global Voices | RSS | Seçildi | İçerik CC BY lisanslı; besleme aktif; robots.txt beslemeye izin veriyor. Kısıtları 4.2 bölümünde. |
| New York Times Developer API | API | Seçildi | Ücretsiz katmanı var, atıf zorunlu. Tam metin yerine özet ve giriş paragrafı veriyor. Guardian'ın yerine ADR-0006 ile kaynak setine alındı. Kısıtları 4.6 bölümünde. |
| Eurasianet | RSS | İleride eklenebilir | İçerik CC BY-ND 4.0 lisanslı (yayıncının kendi yeniden yayın sayfası). Fotoğraf ve multimedya içerik lisansa dahil değil. Beslemesi incelenmedi. |
| ProPublica | RSS | İleride eklenebilir | İçerik Creative Commons lisanslı (yayıncının kendi sayfası). Kaynak gösterme, bağlantı verme ve içeriği düzenlememe şartı var. Lisansın tam türü ve beslemesi incelenmedi. |
| BBC News | RSS | Elendi | Beslemenin telif alanı, yeniden kullanım için BBC kullanım koşullarının "Metadata and RSS feeds" bölümüne yönlendiriyor. Bu bölüme göre beslemeden meta veri (metin, görsel, bağlantı) ayıklanması lisansa, ticari kullanım izne tabi. Not: Bu bilgi resmi sayfanın bir kopyasından okundu. |

### 3.3 Toplayıcılar ve Üçüncü Taraf Beslemeler

| Kaynak | Sonuç | Gerekçe |
|---|---|---|
| Google News, Kagi News | Elendi | Başka yayıncıların içeriğini yeniden dağıtan toplayıcılar. |
| Vatan Gazetesi (chimpfeedr.com üzerinden) | Elendi | Besleme yayıncının kendi alan adında değil, üçüncü taraf bir servis üzerinden sunuluyor. |

## 4. Seçilen Kaynaklar

### 4.1 The Guardian Open Platform

- **Erişim:** REST API, Developer anahtarı ile. Anahtar depoya girmez, gizli bilgi olarak yönetilir.
- **Dil:** İngilizce.
- **Kullanım hakkı:** Open Platform kullanım şartları. Developer paketi ticari olmayan kullanım içindir; bu proje eğitim amaçlı ve ticari olmayan bir projedir.
- **Saklama kısıtı:** Şartların 5. maddesine ("Lifecycle of OP Content") göre içerik en az 24 saatte bir yeniden istenerek yenilenmeli veya silinmelidir. Hiçbir içerik 24 saatten uzun tutulamaz.
- **İstek limiti:** Üçüncü taraf kaynaklarda saniyede 1, günde 500 istek olarak belirtiliyor. Anahtar alınırken resmi erişim sayfasından doğrulanacak.
- **Gelen alanlar:** Üçüncü taraf kaynaklara göre başlık, gövde (tam metin), yazar, bölüm, etiketler, yayın tarihi ve web adresi. API dokümantasyonundan doğrulanacak.
- **Mimariye etkisi:** Guardian içerikleri kalıcı arşive giremez. Veri modelinde, kaynak bazında saklama süresi tanımlanabilmelidir.
> **Not:** Guardian, ADR-0006 ile kaynak setinden çıkarılmıştır. Bu bölüm araştırma tarihindeki bulguları yansıtır.

### 4.2 Global Voices

- **Erişim:** RSS 2.0, `https://globalvoices.org/feed/`
- **Dil:** İngilizce.
- **Kullanım hakkı:** Global Voices Attribution Policy sayfasına göre, aksi belirtilmedikçe içerik CC BY lisanslıdır. Yeniden yayında özgün habere bağlantı ve yazar adı verilmelidir. Besleme de `<copyright>` alanında lisans bilgisini taşıyor.
- **Erişim kuralları:** robots.txt `Crawl-delay: 10` içeriyor (iki istek arasında en az 10 saniye). Besleme adresi kısıtlanmamış.
- **Gelen alanlar:** Başlık, bağlantı, yazar (`dc:creator`), yayın tarihi, kategoriler, `guid`, özet (`description`) ve tam metin (`content:encoded`). Bu alanlar aynı altyapıyı kullanan Türkçe besleme örneğinde gözlendi; İngilizce beslemenin öğeleri toplayıcı geliştirilirken doğrulanacak.
- **Medya:** Başka kişilere ait fotoğraf, video ve ses içeriği aynı lisansla sunulmuyor olabilir. Görsellerin lisansı ayrıca belirtiliyor (örneğin görsel altyazısında). Görsel gösterimi için ayrı bir kural gerekecek.
- **Güncellik:** Araştırma tarihinde beslemenin son güncellemesi 30.10.2026.

### 4.3 TRT Haber

- **Erişim:** RSS 2.0. Besleme listesi ve kategori eşlemeleri ADR-0004'tedir.
- **Dil:** Türkçe.
- **Kullanım hakkı:** Şirket kararı (ADR-0004).
- **Erişim kuralları:** robots.txt besleme adreslerini kısıtlamıyor; yalnızca site içi arama ve hava durumu sayfaları kapalı. `Crawl-delay` kuralı yok.
- **Gelen alanlar:** Başlık, bağlantı, görsel (`<imageUrl>`, standart dışı), özet (`<description>`, CDATA içinde; ayrıca bir HTML yorumu içinde görsel etiketi bulunuyor), kategori, `guid` (haberin adresi) ve yayın tarihi (`+0300`). Tam metin gelmiyor. Gözlem `sondakika.rss` beslemesi üzerinde yapıldı.

### 4.4 NTV

- **Erişim:** Atom. Besleme listesi ve kategori eşlemeleri ADR-0004'tedir.
- **Dil:** Türkçe.
- **Kullanım hakkı:** Şirket kararı (ADR-0004).
- **Erişim kuralları:** robots.txt besleme adreslerini kısıtlamıyor; yapay zekâ şirketlerinin tarayıcıları tamamen engellenmiş. Site Cloudflare koruması arkasında: `HEAD` isteğine HTTP 403, normal `GET` isteğine besleme dönüyor.
- **Gelen alanlar:** `<id>` (haberin adresi), başlık, özet (`<summary>`), tam metin (`<content>`, HTML), yayın ve güncellenme tarihi (`+03:00`), yazar, kategori (`<category term>`), bağlantı ve görsel (`<enclosure>`).
- **Not:** Eski `gundem.rss` adresi resmi besleme listesinde yer almıyor ve başka bir adrese yönlendiriliyor. Gözlem bu yönlendirmenin sonucunda gelen besleme üzerinde yapıldı.

### 4.5 CNN Türk

- **Erişim:** RSS 2.0. Besleme listesi ve kategori eşlemeleri ADR-0004'tedir.
- **Dil:** Türkçe.
- **Kullanım hakkı:** Şirket kararı (ADR-0004).
- **Erişim kuralları:** robots.txt `/feed/` yolunu kısıtlamıyor (`Disallow: /news/` kuralı bu yolu kapsamaz); yapay zekâ şirketlerinin tarayıcıları tamamen engellenmiş.
- **Gelen alanlar:** `guid` (`isPermaLink="true"` beyan edilmiş, ancak değer bir adres değil), bağlantı, başlık, özet (CDATA), yayın tarihi (GMT) ve öğe içinde `<image>` (standart dışı). Kategori alanı yok; kategori haber adresinde yer alıyor. Tam metin gelmiyor.
- **Not:** 03.11.2026 tarihinde kategori beslemelerinin her biri 35 haber döndürüyordu; `bilim-teknoloji` beslemesi boştu. `news` beslemelerinde video sayfalarına giden haberler de bulunuyor.

### 4.6 New York Times Developer API

- **Erişim:** REST API; yalnızca anahtar (`api-key` parametresi) ile. Anahtar depoya girmez.
- **Dil:** İngilizce.
- **Kullanılan API:** Top Stories (`/svc/topstories/v2/{bolum}.json`). Bölümler: arts, automobiles, books/review, business, fashion, food, health, home, insider, magazine, movies, nyregion, obituaries, opinion, politics, realestate, science, sports, sundayreview, technology, theater, t-magazine, travel, upshot, us, world. Archive API (`/svc/archive/v1/{yil}/{ay}.json`) düzenli toplamada kullanılmıyor (ADR-0009).
- **İstek limitleri:** API başına günde 500, dakikada 5 istek; istekler arasında 12 saniye önerilmektedir (FAQ). Yanıt başlıklarında limit bilgisi yok.
- **Önbellek:** Top Stories yanıtları 10 dakika önbellekte tutuluyor (`cache-control: max-age=600`).
- **Gelen alanlar (Top Stories):** `title`, `abstract`, `url`, `uri` (değişmeyen kimlik, `nyt://article/...`), `section`, `subsection`, `byline`, `published_date` ve `updated_date` (New York saatiyle), `multimedia` (farklı boyutlarda görseller, altyazı ve fotoğrafçı bilgisi), konu, yer, kurum ve kişi etiketleri. Tam metin ve giriş paragrafı gelmiyor.
- **Archive gözlemi (04.11.2026):** Kasım 2026 arşivi 1.315 haber ve 3 MB'tı; en yeni haber yaklaşık 12 saat öncesine aitti (tek ölçüm). Alan yapısı Top Stories'ten farklı; `uri` değerleri aynı (Top Stories'ten alınan 5 haberin 4'ü arşivde aynı kimlikle bulundu, biri henüz arşive girmemişti).
- **Kullanım hakkı:** Ticari olmayan kullanım. Branding Guide'a göre atıf zorunlu; içerik değiştirilemez; NYT sayfaları çerçeve içinde gösterilemez. Saklama hükmünün yorumu ADR-0009'dadır.
- **Not:** Geliştirici portalı 10.12.2025'te güncellenmiştir. Portalda Times Newswire API bulunmamaktadır.

## 5. Teknik Bulgular

Bu bölümdeki her bulgu, kaynakların gerçek beslemeleri ve yanıtları incelenerek elde edilmiştir. Her bulgunun altında, mimari ve veri modeli için doğurduğu sonuç belirtilmiştir.

### 5.1 Besleme formatları farklı

İncelenen beslemelerin bir kısmı RSS 2.0 (TRT Haber, CNN Türk, Anadolu Ajansı, Global Voices), bir kısmı Atom (NTV) formatındadır. İki format aynı bilgiyi farklı etiketlerle taşır:

| Bilgi | RSS 2.0 | Atom |
|---|---|---|
| Haber öğesi | `<item>` | `<entry>` |
| Özet | `<description>` | `<summary>` |
| Tam metin | `<content:encoded>` (eklenti) | `<content>` |
| Yayın tarihi | `<pubDate>` | `<published>` |
| Benzersiz kimlik | `<guid>` | `<id>` |

**Sonuç:** Toplayıcı her iki formatı da okuyabilmelidir.

### 5.2 Görsel alanları standart dışı

RSS 2.0'da bir habere görsel eklemenin standart yolu `<enclosure>` veya Media RSS (`media:content`) etiketidir. Gözlemlenen kaynaklar ise görseli farklı biçimlerde veriyor:

| Kaynak | Görsel alanı |
|---|---|
| TRT Haber | `<imageUrl>` (standart dışı) |
| CNN Türk | Öğe içinde `<image>` (standart dışı; RSS 2.0'da `<image>` yalnızca kanal düzeyinde tanımlıdır) |
| Anadolu Ajansı | Öğe içinde `<image>` (standart dışı) |
| NTV | `<enclosure>` (bir RSS etiketi; Atom'daki karşılığı `<link rel="enclosure">` olurdu) |
| Global Voices | Tam metin içindeki HTML `<img>` etiketi |

**Sonuç:** Genel bir besleme okuyucusu bu görsellerin çoğunu bulamaz. Kaynak tanımında, görselin hangi alandan okunacağını belirten bir alan eşleme ayarı bulunmalıdır.

> **13 Kasım 2026 notu (İ-10):** Okuyucu geliştirilirken kullanılan besleme adresleri yeniden incelendi. TRT Haber'in `..._articles.rss` adreslerinde `<imageUrl>` etiketi yok; görsel standart alanlarda (`<enclosure>` ve `media:content`) geliyor. Yukarıdaki TRT gözlemi farklı bir adres (`sondakika.rss`) üzerinde yapılmıştı. Global Voices'ın İngilizce beslemesinde görsel hem tam metindeki `<img>` etiketinde hem de küçük bir önizleme olarak `media:content` alanında geliyor. Sonuç olarak alan eşlemesi yalnızca CNN Türk için gerekti; ayrıntılar ADR-0017'nin 8. bölümündedir.

### 5.3 Benzersiz kimlikler tutarsız

| Kaynak | Kimlik değeri | Not |
|---|---|---|
| TRT Haber | Haberin adresi | `isPermaLink` belirtilmemiş; varsayılan değer `true` |
| CNN Türk | `6ae87cfe2a63731d28ea643e` biçiminde bir değer | `isPermaLink="true"` beyan edilmiş, ancak değer bir adres değil |
| Anadolu Ajansı | `4108183` biçiminde bir sayı | `isPermaLink="false"` |
| NTV | Haberin adresi | Atom `<id>` |
| Global Voices | `https://tr.globalvoices.org/?p=3683` biçiminde bir değer | `isPermaLink="false"` |

**Sonuç:** Kaynakların kimliklerle ilgili beyanlarına güvenilmemelidir. Tekrar tespitinde kimlik tek başına değil, "kaynak + kimlik" birlikteliği olarak kullanılmalıdır. Ek bir kontrol olarak haberin normalize edilmiş adresi kullanılabilir.

### 5.4 Saat dilimleri farklı

TRT Haber ve Anadolu Ajansı tarihleri `+0300`, CNN Türk `GMT`, Global Voices `+0000` ile veriyor. NTV ise ISO 8601 biçiminde (`2026-11-02T15:10:57+03:00`) veriyor.

**Sonuç:** Bütün tarihler UTC'ye çevrilerek saklanmalı, kullanıcıya gösterilirken yerel saate çevrilmelidir. Aksi halde haberlerin tarih sıralaması yanlış olur.

### 5.5 İçerik kapsamı kaynaktan kaynağa değişiyor

TRT Haber, CNN Türk ve Anadolu Ajansı yalnızca özet veriyor. NTV ve Global Voices tam metni HTML olarak veriyor. Guardian API'si de tam metin veriyor.

**Sonuç:** Veri modeli özeti ve tam metni ayrı alanlarda tutmalı, tam metnin bulunmadığı durumu desteklemelidir. Beslemelerden gelen HTML içerik, arayüzde gösterilmeden önce temizlenmelidir. Dış kaynaktan gelen HTML, zararlı betikler (XSS) içerebilir.

### 5.6 Beslemelerde farklı içerik türleri var

CNN Türk'ün haber beslemesinde video sayfalarına giden öğeler (`/video/...`) yer alıyor. Global Voices'ın beslemesi podcast etiketleri de içeriyor.

**Sonuç:** Haberin türü (metin, video vb.) ayırt edilebilmeli, gerekirse filtrelenebilmelidir.

### 5.7 Besleme adresleri değişebiliyor

NTV'nin `https://www.ntv.com.tr/gundem.rss` adresine yapılan istek, yanıt gövdesinde `/turkiye.rss` adresini döndürdü. Yönlendirme takip edildiğinde (`curl -L`) besleme geldi. Aday listesinde bu adres doğrudan çalışır olarak yer alıyordu, yani adres zamanla taşınmış.

**Sonuç:** Toplayıcı yönlendirmeleri sınırlı sayıda takip edebilmeli; kalıcı bir adres değişikliği yöneticiye bildirilmelidir. Bu, şartnamedeki "bir kaynağın bozulması" durumunun somut bir örneğidir.

### 5.8 Bot korumaları

NTV, Cloudflare koruması arkasında. Yalnızca başlık isteyen bir `HEAD` isteğine HTTP 403 döndü, normal `GET` isteğine besleme geldi. Teyit ise `GET` isteğine de HTTP 403 döndürdü.

**Sonuç:** Toplayıcı bir korumayla karşılaştığında onu aşmaya çalışmaz (tarayıcı taklidi, kimlik gizleme vb. yapılmaz). İlgili kaynağı hatalı olarak işaretler ve yöneticiye bildirir. Toplayıcı, isteklerinde kendisini kendi adıyla (`User-Agent`) dürüstçe tanıtır.

### 5.9 robots.txt kuralları

- Global Voices `Crawl-delay: 10` kuralıyla iki istek arasında en az 10 saniye beklenmesini istiyor.
- NTV ve CNN Türk, yapay zekâ şirketlerinin tarayıcılarını (GPTBot, ClaudeBot vb.) tamamen engelliyor.

**Sonuç:** İstek aralığı kaynak bazında ayarlanabilir olmalıdır. Yayıncıların yapay zekâ kullanımına karşı tutumu, yapay zekâ ile ilgili özellikler değerlendirilirken dikkate alınmalıdır.

### 5.10 Beyan edilen dil hatalı olabiliyor

Global Voices Türkçe'nin beslemesi Türkçe içerik yayınladığı halde dil etiketi `en-US`.

**Sonuç:** Kaynağın dili beslemedeki etiketten okunmamalı, kaynak tanımında yönetici tarafından belirlenmelidir.

### 5.11 Lisans bilgisi beslemede yer alabiliyor

Global Voices beslemesinin `<copyright>` alanı içeriğin Creative Commons Attribution lisanslı olduğunu belirtiyor. BBC beslemelerinin aynı alanı ise yeniden kullanım şartlarına yönlendiriyor.

**Sonuç:** Kaynağın lisans ve atıf bilgisi saklanmalı ve haber gösterilirken kullanılmalıdır.

### 5.12 Görsellerin lisansı haberin lisansından ayrı olabiliyor

Global Voices'ta incelenen bir haberin görseli Flickr'dan alınmış ve görsel altyazısında ayrı bir lisansla (CC BY 2.0) belirtilmiş. Global Voices'ın atıf politikası da başka kişilere ait görsellerin aynı şartlarla sunulmayabileceğini belirtiyor. Eurasianet'in lisansı da fotoğraf ve multimedyayı kapsamıyor.

**Sonuç:** Görsel gösterimi için ayrı bir kural gereklidir. Karar: Görseller kopyalanmaz, kaynağın kendi adresinden gösterilir (ADR-0004).

## 6. Hukuki İlkeler

> Bu bölüm bir hukuki görüş değildir. Araştırma sırasında karar verirken esas alınan ilkeleri özetler.

1. **Varsayılan durum "tüm hakları saklıdır".** Telif hukukunda (Türkiye'de 5846 sayılı Fikir ve Sanat Eserleri Kanunu, uluslararası alanda Bern Sözleşmesi) bir eser, sahibi açıkça izin vermedikçe korunur. Bir sitede lisans bildiriminin bulunmaması, içeriğin serbestçe kullanılabileceği anlamına gelmez.
2. **RSS yayınlamak bir kullanım izni değildir.** RSS beslemesi içeriğe teknik bir erişim yolu sağlar. İçeriğin nasıl kullanılabileceğini ise kullanım koşulları veya lisans belirler. İncelenen kaynakların hiçbiri, RSS beslemesinin kullanımına özel bir izin tanımlamıyor.
3. **robots.txt ile kullanım koşulları ayrı şeylerdir.** robots.txt, otomatik erişime ilişkin teknik bir uzlaşımdır, içeriğin kullanım hakkını vermez. TRT Haber'de robots.txt beslemeye izin verirken kullanım koşulları içeriğin arşivlenmesini yasaklıyor. İki kontrol ayrı ayrı yapılmalıdır.
4. **API'lerde bağlayıcı olan, API'nin kullanım şartlarıdır.** robots.txt web taramasına ilişkindir. API erişiminde geçerli kurallar API sağlayıcısının şartlarıdır.
5. **Creative Commons lisanslarının unsurları ayrı ayrı okunmalıdır.**
   - BY (atıf): kaynak ve yazar belirtilmeli.
   - NC (gayriticari): ticari kullanım yasak.
   - ND (türetilemez): içerik değiştirilemez; özetleme gibi işlemler bu kapsamda değerlendirilmelidir.
   - SA (aynı lisansla paylaş): türetilen eser aynı lisansla paylaşılmalı.
   - Lisans, içerikteki üçüncü kişilere ait görselleri kapsamayabilir.
6. **Erişim engelleri ve bot korumaları aşılmaz.** Bu, şartnamenin açık kuralıdır. Erişim engeli bulunan (VOA Türkçe) veya otomatik isteği reddeden (Teyit) kaynaklar bu nedenle elenmiştir.
7. **Bulgular tarihlidir.** Kullanım koşulları değişebilir. Kaynak eklenirken veya düzenli aralıklarla koşullar yeniden kontrol edilmelidir.

## 7. Açık Konular

1. **Türkçe canlı kaynak.** *Çözüldü:* TRT Haber, NTV ve CNN Türk, şirket kararıyla kaynak setine alındı (ADR-0004).
2. **Guardian'ın 24 saat kuralının uygulanması.** *Kapandı:* Guardian kaynak setinden çıkarıldı (ADR-0006).
3. **NYT API'nin kullanım şartları, istek limitleri, gelen alanları, bölüm listesi ve atıf gereklilikleri.** *Çözüldü:* Doğrulama sonuçları 4.6 bölümünde ve ADR-0009'dadır.
4. **Görsel gösterim kuralı.** *Çözüldü:* Görseller kaynaktan indirilip nesne depolamada saklanır (ADR-0010).

## 8. Yöntem ve Kaynaklar

### 8.1 Araştırma süreci

1. **Aday listesi:** İki açık RSS listesi kullanıldı: bir GitHub deposunda bulunan eski tarihli bir liste ve güncel tutulan `github.com/bakinazik/rss` deposu. Bu listeler yalnızca adres sağlar; listedeki bir kaynağın kullanım hakkı ayrıca incelenmiştir.
2. **Ön tarama:** Gemini Deep Research ile bir aday raporu hazırlatıldı.
3. **Birinci el kontroller:** Kararlar, raporun iddialarına değil, aşağıdaki birinci el kontrollere dayanır:
   - robots.txt dosyalarının okunması,
   - beslemelerin ham içeriğinin incelenmesi,
   - HTTP durum kodlarının kontrol edilmesi,
   - kullanım koşulları ve lisans sayfalarının yayıncıların kendi sitelerinden okunması.

### 8.2 Kullanılan komutlar

Beslemenin HTTP başlıklarını görmek için:

```bash
curl -sI https://www.ntv.com.tr/gundem.rss
```

Beslemenin ham içeriğini, yönlendirmeleri takip ederek görmek için:

```bash
curl -sL https://www.ntv.com.tr/gundem.rss | head -40
```

Birden fazla sitede durum kodunu, sayfa boyutunu ve lisans/telif ifadelerini aramak için:

```bash
for site in teyit.org yesilgazete.org www.iklimhaber.org www.newslabturkey.org evrimagaci.org; do
  echo "=== $site ==="
  curl -sL -o /tmp/sayfa.html -w "HTTP %{http_code}, %{size_download} bayt\n" "https://$site"
  grep -ioE "creativecommons[^\"' <]*|telif[^<]{0,60}|copyright[^<]{0,60}|©[^<]{0,60}" /tmp/sayfa.html | sort -u | head -5
done
```

Bu tür aramaların sonuçları dikkatle yorumlanmalıdır. Örneğin İklim Haber'de çıkan "copyright" eşleşmeleri, sayfa düzeninde kullanılan HTML sınıf adları ve sitenin kullandığı bir ikon kütüphanesinin kendi lisans notuydu; haber içeriğinin lisansıyla ilgisi yoktu.

### 8.3 Başvurulan sayfalar

**Kullanım koşulları:**
- TRT Haber: https://www.trthaber.com/kullanim-sartlari.html
- NTV: https://www.ntv.com.tr/kullanim-kosullari
- CNN Türk: https://www.cnnturk.com/yasal-uyari/ ve https://www.cnnturk.com/kullanim-ve-gizlilik-sartlari
- Habertürk: https://www.haberturk.com/kullanimkosullari
- BBC Türkçe: BBC Türkçe sitesindeki "Kullanım koşulları" sayfası

**Lisans ve API şartları:**
- The Guardian Open Platform kullanım şartları: https://www.theguardian.com/open-platform/terms-and-conditions
- Global Voices atıf politikası: https://globalvoices.org/about/global-voices-attribution-policy/
- Eurasianet yeniden yayın kuralları: https://www.eurasianet.org/about/reposting

**Aday listeleri:**
- https://github.com/bakinazik/rss
- https://gist.github.com/e-budur/983d969c0f6cf756bbbb60a2892aa964