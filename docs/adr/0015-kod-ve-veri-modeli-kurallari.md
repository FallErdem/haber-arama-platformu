# ADR-0015: Kod ve Veri Modeli Kuralları

- **Durum:** Kabul edildi
- **Tarih:** 2026-11-04
- **İlişki:** ADR-0005'teki modül adlarını ve ADR-0011'deki iki kararı değiştirir.

## Bağlam

Veri modeli tasarlanırken, bütün tablolar ve kod için geçerli olacak kurallar belirlenmiştir. Bu kuralların bir kısmı daha önce verilen kararları etkilemektedir:

- ADR-0005'te modül adları Türkçe belirlenmişti.
- ADR-0011'de haber tablosunun aylara göre bölümlenmesi ve Elasticsearch'teki ılık indekslerin salt okunur olması kararlaştırılmıştı. Veri modeli tasarımında bu iki kararın, aşağıda açıklanan sorunlara yol açtığı görülmüştür.

## Karar

### 1. Adlandırma

- Kod, tablo ve sütun adları **İngilizcedir.** Dokümanlar ve commit açıklamaları Türkçe kalır (ADR-0002).
  - Gerekçe: Türkçe karakterler adlarda kullanılamadığından bazı Türkçe adlar belirsizleşir. Kullanılan çerçeve ve kütüphanelerin adları İngilizce olduğundan Türkçe adlar iki dilin karıştığı kod üretir.
- Modül adları:

| Eski ad (ADR-0005) | Yeni ad |
|---|---|
| kimlik | `identity` |
| toplama | `ingestion` |
| arama | `search` |
| kullanici | `library` |
| yonetim | `admin` |
| audit | `audit` |

- Tablo adları **çoğul** ve küçük harfle, kelimeler alt çizgiyle ayrılarak yazılır (örnek: `saved_articles`).
  - Gerekçe: Şartnamede geçen kullanıcı tablosunun adı olarak `user` kullanılamaz; `user` PostgreSQL'de ayrılmış bir kelimedir. Bu tablo `users` olarak adlandırılır.

### 2. Birincil anahtarlar

- Birincil anahtarlar `uuid` türündedir ve PostgreSQL 18'in yerleşik `uuidv7()` fonksiyonuyla üretilir.
  - Gerekçe: Sıralı artan sayısal anahtarlar, API'de kayıt sayısını ve sırasını ele verir. Rastgele UUID'ler indekslerde dağınık durup yazma performansını düşürür. UUIDv7 zamana göre sıralı olduğu için bu sorunu taşımaz ve tahmin edilemez. Ayrıca Elasticsearch'teki belge kimliği olarak doğrudan kullanılabilir (ADR-0012).
- Yalnızca iki tabloyu birbirine bağlayan ilişki tablolarında birincil anahtar, iki tablonun anahtarlarından oluşur.

### 3. Zaman alanları

- Bütün zaman alanları saat dilimli (`timestamptz`) tutulur; değerler UTC olarak saklanır (FG-VT-08).
- Her tabloda `created_at` ve `updated_at` alanları bulunur. Hiç güncellenmeyen ilişki tablolarında yalnızca `created_at` bulunur.

### 4. Sabit değer kümeleri

Rol, durum ve tür gibi sabit değer kümeleri `text` türünde saklanır; izin verilen değerler bir `CHECK` kısıtıyla denetlenir.

- Gerekçe: PostgreSQL'in `enum` türünde değerlerin sonradan değiştirilmesi veya silinmesi zahmetlidir. `text` ve `CHECK` ile yeni bir değer, basit bir geçiş betiğiyle eklenir.

### 5. Eş zamanlı güncellemeler

- Yöneticilerin düzenlediği tablolarda (`users`, `sources`, `feeds`) iyimser kilitleme için bir `version` sütunu bulunur. Eski bir sürüm üzerinden yapılan güncelleme reddedilir.
- Uygulamanın kendi yaptığı güncellemeler (toplayıcının zamanlama ve sağlık alanlarını, API'nin kullanıcının oturum ve e-posta alanlarını güncellemesi) sürüm kontrolü yapmaz. Bu güncellemeler yalnızca ilgili alanları değiştiren hedefli sorgularla ve yalnızca değer gerçekten değiştiğinde yapılır. Böylece yönetici düzenlemeleriyle sürüm çakışması oluşmaz.

### 6. Haber tablosunun bölümlenmemesi (ADR-0011'deki kararı değiştirir)

Haber tablosu (`articles`) bölümlenmez.

- Gerekçe: PostgreSQL'de bölümlenmiş tablolarda birincil anahtar ve benzersizlik kısıtları, bölümleme anahtarını içermek zorundadır. Haber tablosu yayın tarihine göre bölümlenirse:
  - Tekrar kontrolü (FG-VT-04) veritabanı tarafından garanti edilemez. Aynı haber farklı bir yayın tarihiyle tekrar geldiğinde farklı bir bölüme düşer ve ikinci kez kaydedilir.
  - Habere bağlanan bütün tablolar, habere kimliğinin yanı sıra yayın tarihiyle de bağlanmak zorunda kalır.
- Bölümlemenin iki temel faydası bu tablo için zayıftır: Haberler hiç silinmediğinden eski bölümlerin kaldırılması gerekmez; aramalar Elasticsearch'te yapıldığından PostgreSQL'deki sorgular genellikle tek bir haberin kimliğiyle getirilmesidir.
- Hacim testinde (FOG-07) PostgreSQL sorgularının yetersiz kaldığı görülürse bu karar yeniden değerlendirilecektir.
- Bölümleme, bu sorunları taşımayan audit log tablosunda kullanılır (ADR-0016).

### 7. Ilık ve soğuk indekslerin yazmaya açık kalması (ADR-0011'deki kararı değiştirir)

Elasticsearch'teki ılık ve soğuk indeksler birleştirilir (force merge), ancak salt okunur yapılmaz.

- Gerekçe: Salt okunur bir indekse yazılamadığı gibi, indeksten belge de silinemez. Bu durumda eski bir haberin gizlenmesi (gizlenen haberin indeksten silinmesi) ve ay sınırında gecikmeli gelen haberlerin önceki ayın indeksine yazılması başarısız olur. Bu indekslere yazma çok nadir olduğundan birleştirmenin faydası büyük ölçüde korunur.

## Sonuçlar

- ADR-0005'te ve mimari dokümanında geçen modül adları yeni adlarla güncellenir.
- Veri modeli bu kurallara göre tasarlanır (`05-veri-modeli.md`).
- Haber tablosunda tekrar kontrolü doğrudan benzersizlik kısıtlarıyla garanti edilir; habere bağlanan tablolar habere yalnızca kimliğiyle bağlanır.
- Yaşam döngüsünün PostgreSQL'deki karşılığı, her haberin durum bilgisidir.