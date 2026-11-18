# ADR-0019: Haber Metinlerinin Yalnızca Elasticsearch'te Tutulması

- **Durum:** Kabul edildi; iki adımda uygulandı (1. adım, 17 Kasım: arama indeksinin tamamlanması; 2. adım, 18 Kasım: PostgreSQL'deki metin sütunlarının kaldırılması)
- **Tarih:** 2026-11-17
- **İlişki:** ADR-0011'deki "PostgreSQL haberlerin bütün bilgilerinin asıl kaydıdır" kararını ve ADR-0012'deki tam yeniden indekslemenin kaynağını değiştirir.

## Bağlam

ADR-0011'e göre PostgreSQL haberlerin bütün bilgilerini (başlık, özet, tam metin, yazar dahil) tutan asıl kayıttı; Elasticsearch bunların aranabilir bir kopyasıydı. Özet ve tam metin böylece iki depoda birden duruyordu.

17 Kasım 2026'daki revize görüşmesinde, verinin iki depoda tekrarlanmaması istendi: haber metinleri Elasticsearch'te, meta veri PostgreSQL'de tutulmalı ve gerektiğinde ikisi birleştirilmeli. Bu, projenin başındaki "PostgreSQL meta veriyi ve haberlerin yaş bilgisini tutuyor" yönlendirmesiyle de örtüşür. Hedef ölçek 1 milyon haberdir; metin alanları haber kaydının en büyük kısmıdır.

## Karar

**Özet, tam metin ve yazar yalnızca Elasticsearch'te tutulur. PostgreSQL haberin meta verisini tutar.**

| Bilgi | Nerede |
|---|---|
| Kimlik, kaynak, özgün adres ve normalleştirilmiş adres, dış kimlik, dil, tür, yayın ve toplanma zamanı, yaşam döngüsü durumu, gizleme bilgisi, grup kimliği, kategoriler, görseller | PostgreSQL |
| Başlık | PostgreSQL ve Elasticsearch |
| Özet, tam metin (HTML), yazar | Yalnızca Elasticsearch |

**Başlık iki depoda da durur.** Başlık haberin kimliğinin bir parçasıdır ve arama dışındaki ekranlar ona ihtiyaç duyar: kaydedilen haberler listesi, yönetim ekranları (gizlenen haberler, kaynak içeriği silme), audit kayıtları ve kaynaklar arası gruplama. Bu işlevler Elasticsearch kapalıyken de çalışmalıdır (FOG-09). Başlık kısadır; asıl yer tutan özet ve tam metindir.

**Tam metin Elasticsearch'te HTML olarak, tek alanda saklanır.** Detay sayfası metni paragraflarıyla gösterir. Aramadan önce etiketler atılır ve kodlanmış karakterler çözülür (`html_strip` karakter süzgeci); etiket ve bağlantı adresleri aranabilir kelime olmaz. Metnin ayrıca düz metin olarak ikinci bir alanda tutulması değerlendirildi; daha basit olurdu, ancak metin Elasticsearch'in içinde iki kez durur ve bu kararın amacıyla çelişirdi.

Yerleşik `turkish` ve `english` analizörlerine karakter süzgeci eklenemediğinden ikisi Elastic'in dokümanındaki tanımlarıyla yeniden kurulur (`turkish_article`, `english_article`) ve başına `html_strip` konur. HTML'siz metinde yerleşik analizörlerle birebir aynı kelimeleri ürettikleri testle denetlenir. Bir dilin bütün metin alanları (başlık, özet, tam metin) aynı analizörü kullanır: arama, kelimelerin farklı alanlarda geçmesine izin veren `cross_fields` yöntemini kullanır ve Elasticsearch yalnızca aynı analizörlü alanları birlikte değerlendirir. Tam metne ayrı bir analizör verildiğinde "galatasaray" başlıkta, "fenerbahçe" tam metinde geçen haberin bulunamadığı API testinde görüldü.

### Uygulama adımları

Geçiş, veri kaybı olmayacak şekilde iki adımda yapılır.

**1. adım: Arama indeksinin tamamlanması.** Elasticsearch'te tam metin şimdiye kadar düz metin olarak duruyordu ve yazar hiç yoktu; detay sayfası ikisine de ihtiyaç duyar. Şablona HTML'li tam metin ve yazar eklenir; tam yeniden indeksleme PostgreSQL'den (metinler henüz oradayken) yapılır. PostgreSQL'e dokunulmaz.

**2. adım: Okuma ve yazmanın değişmesi, sütunların kaldırılması.**

- Kaydetme: özet, tam metin ve yazar PostgreSQL'e yazılmaz; haberle aynı işlemde yazılan outbox notuna (`outbox_events.payload`, `jsonb`) konur. Haber ve not tek işlemde yazıldığından hiçbir metin kaybolmaz (ADR-0012).
- Outbox aktarımı: metinleri nottan, meta veriyi PostgreSQL'den alır. Not işlenince metin nottan da silinir; PostgreSQL'de metnin kopyası kalmaz. Sonradan gelen meta veri değişiklikleri (kategori eklenmesi, gizleme) belgenin yalnızca ilgili alanlarını günceller.
- API: arama sonuçlarındaki özet ve haber detayındaki özet, tam metin ve yazar Elasticsearch'ten okunur. Elasticsearch kapalıyken haber detayı `503 SEARCH_UNAVAILABLE` döner: metni olmayan bir detay sayfası kullanıcıya bozuk görünür. Yalnızca başlık gereken ekranlar çalışmaya devam eder.
- Tam yeniden indeksleme: kaynak artık eski Elasticsearch nesli olur (Elasticsearch'in `_reindex` işlemi); meta veri PostgreSQL'den tazelenir.
- Yeni bir geçiş betiği (V14) özet, tam metin ve yazar sütunlarını kaldırır. Betik API açılırken çalıştığından, dağıtım sırasında işçi birkaç dakika durdurulur; eski işçinin kaldırılan sütunlara yazmaya çalışması önlenir.
- V14, sütunları silmeden önce Elasticsearch'te karşılığı olmayan metinleri outbox notlarına taşır: işlenmemiş notlara (işçi durdurulduğu an son kaydettiği haberlerin notları henüz aktarılmamış olabilir) haberin metni konur; gizlenmiş her haber için metniyle yeni bir not yazılır (eski düzende belgeleri indeksten silinmişti). Böylece silme anında bekleyen bir not olsa da metin kaybolmaz; "bekleyen not kalmayana kadar bekle" kuralı, işçi beslemeleri sürekli okuduğu için güvenilir değildi. Kümede uygulama sırası `scripts/dev/apply-v14.sh` betiğindedir: işçiyi durdurur, görünür her haberin belgesi ya da bekleyen notu olduğunu sayılarla denetler, onay ister, önce API'yi (V14), sonra durdurulmuş işçiyi günceller ve yeniden indeksleme yapar (`hidden` alanı yalnızca yeni açılan indekslere girer).

**2. adımda verilen ek kararlar**

- **Gizlenen haberin belgesi indekste kalır.** Belgeye `hidden` alanı eklenir; haber gizlendiğinde belge `hidden: true` olarak güncellenir ve arama bu belgeleri sorguda dışarıda bırakır. Önceden gizlenen haberin belgesi siliniyor, gizleme geri alınınca PostgreSQL'deki metinlerle yeniden yazılıyordu. Metinlerin tek kaydı belge olduğundan silmek, gizlemeyi geri alınamaz hale getirirdi. Değerlendirilen diğer seçenek, gizlenen haberin metinlerinin PostgreSQL'de ayrı bir tabloya taşınmasıydı; metni yeniden iki depoya bölerdi ve gizleme ile geri alma birer veri taşıma işi olurdu.
- **Haber gizlendiğinde de `INDEX` notu yazılır.** Not "belgeyi güncel haline getir" anlamındadır; `DELETE` notu yalnızca haber silindiğinde (kaynak içeriğinin silinmesi) yazılır.
- **Haber detayı API'de `search` modülüne taşınır.** Detay artık Elasticsearch'e de ihtiyaç duyar; API'de Elasticsearch'e yalnızca `search` modülü erişir ve modüllerin yönü `search → ingestion`'dır. Detay `ingestion`'da kalsaydı `ingestion → search` bağımlılığı döngü oluştururdu. Meta veri ve görseller `ingestion` modülünün `ArticleCatalog` arayüzünden (`findDetails`) alınır.
- **Belgesi henüz aktarılmamış haberin detayı metinsiz döner.** Haber kaydedildikten sonraki birkaç saniye içinde (outbox notu işlenene kadar) detay istenirse başlık, kaynak ve görseller döner; özet, tam metin ve yazar `null` olur.

## Sonuçlar

- Metinler tek bir depoda durur; PostgreSQL küçülür.
- Elasticsearch artık türetilmiş bir kopya değil, metinlerin tek kaydıdır. Yedeklenmesi zorunlu hale gelir (İ-34; Elasticsearch yedeği MinIO'ya alınabilir). Risk kaydında R-38.
- "İki depo tutarsız" durumunda metinleri yeniden üretecek ikinci bir kaynak kalmaz. Tam yeniden indeksleme indeks yapısı değişikliği için çalışmaya devam eder; meta veri tutarsızlıkları PostgreSQL'den giderilir (R-20).
- Haber detayı iki depodan birleştirilerek üretilir.
- Elasticsearch kapalıyken haber detayı da kullanılamaz (aramaya ek olarak).
