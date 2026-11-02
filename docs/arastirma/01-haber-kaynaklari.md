# Haber Kaynakları Araştırması

- **Araştırma tarihi:** 2 Kasım 2026
- **İlgili karar:** ADR-0003

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

Kullanım hakkı kriteri belirleyici kabul edilmiştir: Teknik olarak ne kadar uygun olursa olsun, kullanım hakkı açık olmayan bir kaynak seçilmemiştir.

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

### 3.2 İngilizce Kaynaklar

| Kaynak | Tür | Sonuç | Gerekçe |
|---|---|---|---|
| The Guardian Open Platform | API | Seçildi | Ücretsiz Developer anahtarı ticari olmayan kullanıma açık; tam metin veriyor. Kısıtları 4.1 bölümünde. |
| Global Voices | RSS | Seçildi | İçerik CC BY lisanslı; besleme aktif; robots.txt beslemeye izin veriyor. Kısıtları 4.2 bölümünde. |
| New York Times Developer API | API | İleride eklenebilir | Ücretsiz katmanı var, atıf zorunlu. Tam metin yerine özet ve giriş paragrafı veriyor. İstek limitleri için farklı kaynaklarda farklı değerler geçiyor; resmi sayfadan doğrulanmadı. Başlangıçta tek API kaynağı yeterli görüldü. |
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

### 4.2 Global Voices

- **Erişim:** RSS 2.0, `https://globalvoices.org/feed/`
- **Dil:** İngilizce.
- **Kullanım hakkı:** Global Voices Attribution Policy sayfasına göre, aksi belirtilmedikçe içerik CC BY lisanslıdır. Yeniden yayında özgün habere bağlantı ve yazar adı verilmelidir. Besleme de `<copyright>` alanında lisans bilgisini taşıyor.
- **Erişim kuralları:** robots.txt `Crawl-delay: 10` içeriyor (iki istek arasında en az 10 saniye). Besleme adresi kısıtlanmamış.
- **Gelen alanlar:** Başlık, bağlantı, yazar (`dc:creator`), yayın tarihi, kategoriler, `guid`, özet (`description`) ve tam metin (`content:encoded`). Bu alanlar aynı altyapıyı kullanan Türkçe besleme örneğinde gözlendi; İngilizce beslemenin öğeleri toplayıcı geliştirilirken doğrulanacak.
- **Medya:** Başka kişilere ait fotoğraf, video ve ses içeriği aynı lisansla sunulmuyor olabilir. Görsellerin lisansı ayrıca belirtiliyor (örneğin görsel altyazısında). Görsel gösterimi için ayrı bir kural gerekecek.
- **Güncellik:** Araştırma tarihinde beslemenin son güncellemesi 30.10.2026.