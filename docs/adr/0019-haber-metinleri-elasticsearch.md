# ADR-0019: Haber Metinlerinin Yalnızca Elasticsearch'te Tutulması

- **Durum:** Kabul edildi; iki adımda uygulanıyor (1. adım: arama indeksinin tamamlanması; 2. adım: PostgreSQL'deki metin sütunlarının kaldırılması)
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

- Kaydetme: özet, tam metin ve yazar PostgreSQL'e yazılmaz; haberle aynı işlemde yazılan outbox notuna konur. Haber ve not tek işlemde yazıldığından hiçbir metin kaybolmaz (ADR-0012).
- Outbox aktarımı: metinleri nottan, meta veriyi PostgreSQL'den alır. Not işlenince metin nottan da silinir; PostgreSQL'de metnin kopyası kalmaz. Sonradan gelen meta veri değişiklikleri (kategori eklenmesi, gizleme) belgenin yalnızca ilgili alanlarını günceller.
- API: arama sonuçlarındaki özet ve haber detayındaki özet, tam metin ve yazar Elasticsearch'ten okunur. Elasticsearch kapalıyken haber detayı `503 SEARCH_UNAVAILABLE` döner: metni olmayan bir detay sayfası kullanıcıya bozuk görünür. Yalnızca başlık gereken ekranlar çalışmaya devam eder.
- Tam yeniden indeksleme: kaynak artık eski Elasticsearch nesli olur (Elasticsearch'in `_reindex` işlemi); meta veri PostgreSQL'den tazelenir.
- Yeni bir geçiş betiği (V14) özet, tam metin ve yazar sütunlarını kaldırır. Betik API açılırken çalıştığından, dağıtım sırasında işçi birkaç dakika durdurulur; eski işçinin kaldırılan sütunlara yazmaya çalışması önlenir.

## Sonuçlar

- Metinler tek bir depoda durur; PostgreSQL küçülür.
- Elasticsearch artık türetilmiş bir kopya değil, metinlerin tek kaydıdır. Yedeklenmesi zorunlu hale gelir (İ-34; Elasticsearch yedeği MinIO'ya alınabilir). Risk kaydında R-38.
- "İki depo tutarsız" durumunda metinleri yeniden üretecek ikinci bir kaynak kalmaz. Tam yeniden indeksleme indeks yapısı değişikliği için çalışmaya devam eder; meta veri tutarsızlıkları PostgreSQL'den giderilir (R-20).
- Haber detayı iki depodan birleştirilerek üretilir.
- Elasticsearch kapalıyken haber detayı da kullanılamaz (aramaya ek olarak).
