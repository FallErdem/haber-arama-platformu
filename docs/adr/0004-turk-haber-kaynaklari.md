# ADR-0004: Türk Haber Kaynaklarının Eklenmesi

- **Durum:** Kabul edildi; Guardian ile ilgili kısımları ADR-0006 ile geçersiz kılındı; görsel kuralı ADR-0010 ile değiştirildi
- **Tarih:** 2026-11-03
- **İlişki:** ADR-0003'ü genişletir. ADR-0003'teki Guardian ve Global Voices kararları geçerliliğini korur.

## Bağlam

Kaynak araştırmasında (`docs/arastirma/01-haber-kaynaklari.md`) incelenen Türk haber sitelerinin kullanım koşullarının içeriğin saklanmasını ve başkalarına sunulmasını yazılı izne bağladığı tespit edilmiş, bu nedenle ADR-0003'te başlangıç kaynak setine Türkçe kaynak alınmamıştı.

03.11.2026 tarihinde yönetici ile yapılan görüşmede, uygulamanın yalnızca geliştirici tarafından kullanılacağı ve kimseye açılmayacağı belirtilmiş; bu nedenle TRT Haber ve benzeri Türk haber sitelerinin RSS beslemelerinin okunup haberlerin depolanabileceği bildirilmiştir. Bot koruması, erişim engeli veya ödeme duvarı gibi teknik korumaların aşılması bu kararın kapsamında değildir.

## Karar

### 1. Kaynaklar

TRT Haber, NTV ve CNN Türk, RSS/Atom beslemeleriyle kaynak setine eklenir.

Habertürk, kullanım koşullarında içeriğin bot ve tarayıcılarla toplanmasını açıkça yasakladığından (md. 8) şimdilik eklenmez. BBC Türkçe ve diğer Türk kaynakları ileride değerlendirilebilir.

### 2. Kullanım kuralları

- Kaynakların robots.txt kurallarına ve tanımlı istek aralıklarına uyulur.
- Teknik korumalar aşılmaz. Normal bir istekle erişilemeyen besleme kullanılmaz ve hatalı olarak işaretlenir.
- Her haberde özgün kaynağın adı ve özgün habere bağlantı gösterilir; içerik değiştirilmez.
- Görseller kopyalanmaz, kaynağın kendi adresinden gösterilir. Bu kural tüm kaynaklar için geçerlidir.
- Haberler süresiz saklanır.
- Bir kaynağın talebi halinde ilgili içerik gizlenir.

### 3. Ortak kategori listesi

Kaynakların kategorileri aşağıdaki ortak listeye eşlenir:

Gündem, Dünya, Ekonomi, Spor, Sağlık, Bilim ve Teknoloji, Kültür ve Sanat, Yaşam, Son Dakika, Diğer.

- Bir haber birden fazla kategoriye sahip olabilir.
- Eşleme iki düzeyde yapılır:
  - **Besleme düzeyi:** Konuya özel bir besleme doğrudan bir kategoriye eşlenir.
  - **Haber düzeyi:** Karışık içerikli beslemelerde kategori, her haberin kaynakta belirtilen kendi kategori bilgisinden (kategori alanı veya haber adresi) bulunur.
- Eşlenemeyen kategoriler "Diğer" kategorisine atanır.
- **Son Dakika** bir konu değil, zaman etiketidir. Son dakika beslemelerinden gelen haberler, yapılandırılabilir bir süre boyunca (varsayılan 6 saat) Son Dakika kategorisinde görünür; konu kategorileri kalıcıdır.

### 4. Beslemeler ve kategori eşlemeleri

Besleme adresleri kaynakların kendi resmi besleme listelerinden alınmıştır. Adreslerin çalıştığı toplayıcı geliştirilirken doğrulanacaktır.

#### TRT Haber (RSS 2.0)

Adres biçimi: `https://www.trthaber.com/{besleme}_articles.rss`

| Besleme | Kategori |
|---|---|
| `gundem`, `turkiye` | Gündem |
| `dunya` | Dünya |
| `ekonomi` | Ekonomi |
| `spor` | Spor |
| `saglik` | Sağlık |
| `bilim_teknoloji` | Bilim ve Teknoloji |
| `kultur_sanat` | Kültür ve Sanat |
| `yasam`, `egitim` | Yaşam |
| `sondakika` | Son Dakika + haber düzeyi |
| `manset`, `guncel`, `koronavirus`, `infografik`, `interaktif`, `ozel_haber`, `dosya_haber` | Haber düzeyi |

#### NTV (Atom)

Adres biçimi: `https://www.ntv.com.tr/{besleme}.rss`

| Besleme | Kategori |
|---|---|
| `turkiye` | Gündem |
| `dunya` | Dünya |
| `ekonomi`, `ntvpara` | Ekonomi |
| `sporskor` | Spor |
| `saglik` | Sağlık |
| `teknoloji` | Bilim ve Teknoloji |
| `yasam`, `egitim`, `otomobil` | Yaşam |
| `son-dakika` | Son Dakika + haber düzeyi |
| `galeri`, `video` | Haber düzeyi |

NTV'nin kültür ve sanat beslemesi bulunmamaktadır.

#### CNN Türk (RSS 2.0)

Adres biçimi: `https://www.cnnturk.com/feed/rss/{besleme}/news`

| Besleme | Kategori |
|---|---|
| `turkiye` | Gündem |
| `dunya` | Dünya |
| `ekonomi` | Ekonomi |
| `spor` | Spor |
| `saglik` | Sağlık |
| `kultur-sanat` | Kültür ve Sanat |
| `yasam`, `egitim`, `otomobil` | Yaşam |
| `all` | Haber düzeyi (haber adresinden) |

`bilim-teknoloji` beslemesi 03.11.2026 tarihinde boş olduğundan eklenmemiştir; bu kategorideki haberler `all` beslemesi üzerinden haber düzeyinde eşlenir.

#### Guardian ve Global Voices

- **Guardian:** Haber düzeyinde, haberin bölüm (section) bilgisine göre eşlenir. Eşleme tablosu API anahtarı alındıktan sonra hazırlanacaktır.
- **Global Voices:** Varsayılan kategori Dünya'dır. Haberin konu kategorilerinden ortak listeyle eşleşenler ek olarak eşlenir; bölge kategorileri eşlenmez.

## Sonuçlar

- Türkçe içerik ilk sürümden itibaren toplanacağından, Türkçe dil analizi ilk sürümün parçasıdır.
- Türk kaynakları ajans haberlerini büyük ölçüde aynen yayımladığından, kaynaklar arası tekrar eden haberlerin gruplanması gerekir.
- Veri modeli, haber ile kategori arasında çoka çok ilişkiyi ve iki düzeyli eşleme kurallarını desteklemelidir.
- Kaynak başına çok sayıda besleme bulunduğundan kaynaklara yapılan istek sayısı artar. Toplama sıklığı besleme bazında ayarlanabilir olmalıdır.
- Görseller kaynakların adreslerinden gösterileceğinden, güvenlik başlıklarında bu alan adlarına izin verilmelidir.
- Kaynakların kullanım koşullarıyla çelişki riski şirket tarafından kabul edilmiştir; risk kaydında ayrıca izlenir.