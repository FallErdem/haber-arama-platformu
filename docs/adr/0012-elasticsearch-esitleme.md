# ADR-0012: PostgreSQL ile Elasticsearch'ün Eşitlenmesi

- **Durum:** Kabul edildi; outbox işlemi ADR-0017 ile Python işçisine taşındı
- **Tarih:** 2026-11-04

## Bağlam

ADR-0011'e göre PostgreSQL asıl kayıttır, Elasticsearch ise PostgreSQL'den türetilen bir arama indeksidir. PostgreSQL'deki haber kayıtlarında yapılan değişikliklerin (yeni haber, gizleme, gizlemenin geri alınması, silme) Elasticsearch'e yansıması gerekir. Aksi halde depolar arasında tutarsızlık oluşur; örneğin gizlenen bir haber aramada görünmeye devam eder (R-20, FG-AR-09).

Şartnamenin dayanıklılık testi, bir servis veya veritabanı erişilemez olduğunda sistemin nasıl davrandığını sormaktadır. Elasticsearch geçici olarak erişilemez olduğunda yapılan değişiklikler kaybolmamalıdır.

## Değerlendirilen Seçenekler

### 1. Çift yazma

Uygulama önce PostgreSQL'e, hemen ardından Elasticsearch'e yazar.

- Artı: En kolay uygulanabilir yöntemdir.
- Eksi: PostgreSQL'e yazıldıktan sonra Elasticsearch'e yazma başarısız olursa iki depo tutarsız kalır.

### 2. Outbox deseni

Kayıt değişikliği ile "bu kayıt Elasticsearch'e aktarılacak" bilgisi PostgreSQL'e aynı işlem (transaction) içinde yazılır. Ayrı bir iş bu bilgileri okuyup Elasticsearch'e aktarır.

- Artı: Değişiklik ile aktarım bilgisi birlikte yazıldığından hiçbir değişiklik kaybolmaz; aktarım başarısız olursa daha sonra yeniden denenir.
- Artı: Ek bir altyapı bileşeni gerektirmez.
- Eksi: Ek bir tablo ve bu tabloyu işleyen bir iş gerekir; değişikliğin aramaya yansıması birkaç saniye gecikir.

### 3. Değişiklik verisi yakalama (CDC)

PostgreSQL'in değişiklik günlüğü (WAL) Debezium gibi bir araçla izlenir; değişiklikler bir mesaj aracısı (Kafka) üzerinden Elasticsearch'e aktarılır.

- Artı: Uygulama kodundan bağımsızdır.
- Eksi: Kafka ve Debezium gibi kaynak tüketimi yüksek ek bileşenler gerektirir; bu projenin ölçeği için gereğinden ağırdır.

### 4. Periyodik toplu eşitleme

Belirli aralıklarla, son eşitlemeden sonra değişen kayıtlar Elasticsearch'e aktarılır.

- Eksi: Değişikliklerin yansıması aralığın uzunluğu kadar gecikir; silmelerin yakalanabilmesi için kayıtların silinmek yerine işaretlenmesi gerekir.

## Karar

**Outbox deseni** uygulanacaktır.

- Bir haber kaydı oluşturulduğunda, güncellendiğinde, gizlendiğinde, gizlemesi geri alındığında veya silindiğinde, aynı işlem içinde outbox tablosuna bir kayıt eklenir. Kayıt; haberin kimliğini, yapılacak işlemi (indeksle veya sil) ve oluşturulma zamanını içerir.
- Outbox tablosunu işleyen iş, toplayıcı rolünde birkaç saniyede bir çalışır (ADR-0005). Başarıyla aktarılan kayıtlar işlenmiş olarak işaretlenir; başarısız olanlar sonraki çalışmada yeniden denenir.
- Aktarım işlemi tekrarlanabilir (idempotent) olacak şekilde tasarlanır: Aynı kayıt birden fazla kez aktarılsa da sonuç değişmez. Bunun için Elasticsearch'teki belge kimliği, PostgreSQL'deki haber kimliğiyle aynıdır.
- Aynı habere ait outbox kayıtları oluşturulma sırasıyla işlenir.
- İşlenmiş outbox kayıtları belirli bir süre sonra temizlenir.
- Bunlara ek olarak, Elasticsearch indeksini PostgreSQL'den baştan oluşturan bir **tam yeniden indeksleme** işi bulunur. Bu iş, tutarsızlık şüphesi olduğunda veya indeks yapısı değiştiğinde elle başlatılır.

## Sonuçlar

- Bir değişikliğin aramaya yansıması birkaç saniye gecikir. Örneğin gizlenen bir haber birkaç saniye daha aramada görünebilir.
- Elasticsearch erişilemez olduğunda değişiklikler outbox tablosunda birikir ve Elasticsearch yeniden erişilebilir olduğunda aktarılır.
- Outbox tablosunun büyümesi, işlenmiş kayıtların temizlenmesiyle sınırlanır.
- Tam yeniden indeksleme, R-20'nin önlemidir.