# Hafta 3 İlerleme Notu (16–20 Kasım 2026)

## Yapılanlar

- Hafta 2'den kalan haber toplama işleri tamamlandı (İ-10 – İ-12): RSS ve Atom okuyucusu, iki düzeyli kategori eşlemesi, tekrar kontrolü, yeniden deneme ve beslemenin kendiliğinden devre dışı kalması. Gerçek toplamada bulunan iki hata düzeltildi. Kümede dört kaynağın 42 beslemesinden haberler düzenli toplanıyor (yaklaşık 2.900 haber).
- Arama indeksi kuruldu (İ-15): Türkçe ve İngilizce analizörler, Türkçe karaktersiz yazımı da eşleştiren ikinci bir alan, aylık indeksler ve yaşam döngüsü politikası; veritabanındaki değişiklikleri indekse taşıyan outbox aktarımı ve tam yeniden indeksleme betiği.
- Arama API'si yazıldı (İ-17): filtreler, sıralama, vurgulama, sayfalama ve Son Dakika süresi. Sorgunun kuralları gerçek haberlerle denenerek seçildi; kelimeleri yan yana içeren haber üstte çıkıyor, tırnak içindeki öbek zorunlu.
- Görsel indirme eklendi (İ-14): içerik doğrulaması, 20 MB sınırı, WebP'ye çevirip en uzun kenarı 1600 piksele küçülterek MinIO'ya yükleme.
- Haber detayı ve görsellerin imzalı, süreli adresleri eklendi (İ-18).
- Haber metinleri (özet, tam metin, yazar) PostgreSQL'den çıkarılıp yalnızca Elasticsearch'te tutulur hale getirildi (ADR-0019). Kümedeki veriler bir geçiş betiğiyle taşındı; 2.856 haberin hepsi eksiksiz aktarıldı.
- CNN Türk haberlerinin yayın saatlerinin 3 saat ileri kaydedildiği fark edildi; kaynağa saat dilimi ayarı eklendi ve eski kayıtlar düzeltildi (V15).
- Arama ve haber detayı ekranları yazıldı (İ-19): filtreler, tarih seçimi, Son Dakika, vurgulama, numaralı sayfalama; arama durumu adres çubuğunda tutulduğu için aramalar paylaşılabiliyor. Oturum süresi dolduğunda yeniden giriş, pasif yapılan kullanıcıda hesap durumu ekranı.
- Kaydedilen haberler eklendi (İ-20): arama sonuçlarından ve detaydan yer imiyle kaydetme, Kaydedilenler sayfası, gizlenen haberin listede belirtilmesi.
- Audit altyapısı kuruldu (İ-16): kullanıcı kaydı, yeni oturum ve reddedilen istekler kaydediliyor; kayıtlarda token, şifre ve arama ifadesi bulunmuyor.
- Yönetim panelinin ilk ekranı yazıldı (İ-21): kullanıcıları listeleme ve arama, onaylama, reddetme, rol ve durum değiştirme, son aktif yönetici kuralı. Bütün işlemler, reddedilen denemeler de dahil, audit log'a yazılıyor.
- Kök README ve boş bir Ubuntu bilgisayarda sıfırdan kurulumu anlatan doküman yazıldı.
- Testler: API 156, işçi 394, frontend 150.

## Devam edenler

- İ-13 (NYT okuyucusu), İ-22 (kaynaklar ve beslemeler), İ-23 (audit arama ve dışa aktarma), İ-24 (kaynak içeriğinin silinmesi), İ-25 (pano), İ-26 (yaşam döngüsü ve temizlik işleri) ile Should ve Could iş kalemleri (İ-27 – İ-31) sırada; Cuma ve hafta sonu tamamlanacak.

## Alınan kararlar

- **Haber metinleri yalnızca Elasticsearch'te:** Metinler PostgreSQL'de ve indekste iki kez tutuluyordu. PostgreSQL meta veriyi (başlık, kaynak, tarih, durum) tutuyor; yeni haberin metni indekse outbox notuyla taşınıyor ve not işlenince siliniyor. Gizlenen haberin belgesi indekste gizli olarak işaretleniyor (ADR-0019).
- **Arama sorgusunun kuralları:** Başlıktaki eşleşme en yüksek, tam metindeki en düşük ağırlıkta; bir veya iki kelimelik aramada kelimelerin hepsi, daha uzun aramada dörtte üçü geçmeli; Türkçe karaktersiz eşleşme düşük ağırlıkta (veri modeli 5.5).
- **Görseller WebP olarak:** En uzun kenar 1600 piksel, orijinal saklanmıyor. Kaynaklardan 5,3 MB'a ve 8256 × 5504 piksele kadar görseller geliyordu; arayüzde bir görsel en fazla ekran genişliğinde gösteriliyor. AVIF daha küçük ama sıkıştırması çok daha yavaş (ADR-0017).
- **İmzalı görsel adresleri:** Görseller token yerine süreli imzayla açılıyor, çünkü `<img>` etiketi istek başlığı ekleyemiyor. Süre saat başına yuvarlandığı için tarayıcı aynı görseli önbellekten kullanabiliyor (API sözleşmesi 4.4).
- **Kaynağa özel saat dilimi:** Saat dilimini yanlış yazan kaynak için okuyucu beslemedeki saati kaynağın ayarındaki saat diliminde okuyor (ADR-0017).
- **Modüllerin yönü:** Haber detayı, metinler Elasticsearch'te olduğu için arama modülünde. Kaydedilen haberler modülü haber bilgisini veri toplama modülünden alıyor; arama modülü "kaydedildi mi" bilgisini kaydedilen haberler modülüne soruyor. Döngü yok; bunu bir test her derlemede denetliyor (mimari, 4. bölüm).
- **Arayüz araçları:** shadcn/ui'ın React Aria tabanlı stili (klavye ve ekran okuyucu desteği hazır geliyor), Tailwind, React Router ve adres parametreleri için Zod. Tasarım sade, gazete düzeninde (ADR-0018).
- **Kaydet düğmesi aç/kapa düğmesi:** Düğmenin adı durumla değişmiyor, ekran okuyucu "Kaydet, basılı" diyor.(ekran akışları 5.1).
- **Audit kuralları:** Bir işlem ve kaydı aynı veritabanı işleminde yazılıyor. Kimliği doğrulanmış kullanıcının reddedilen istekleri yazılıyor, kimliği doğrulanamayanlar yazılmıyor. İş kuralıyla reddedilen yönetim işlemleri de "başarısız" olarak yazılıyor (ADR-0016, veri modeli 3.13).
- **IP adresi ağ geçidinden:** İstemcinin kendisinin gönderebildiği başlığa güvenilmiyor. (ADR-0016).
- **Son aktif yönetici kuralında kilit:** İki yönetici aynı anda birbirinin rolünü düşürürse sistemde yönetici kalmayabilirdi; bu değişiklikler bir veritabanı kilidiyle sıraya sokuluyor (API sözleşmesi 6.1).

## Öğrenilenler

- **Outbox deseni:** Veritabanına yazma ile arama indeksine yazma tek işlemde yapılamıyor. Değişiklik, veritabanında aynı işlemde bir nota yazılıyor; işçi notları sırayla indekse taşıyor. Elasticsearch kapalıyken notlar bekliyor, kayıp olmuyor.
- **Elasticsearch analizörleri:** Kelimelerin köke indirilmesi, büyük/küçük harf ve Türkçe karakterlerin ASCII'ye çevrilmesi. Alan yapısı değişince indeksin yeniden oluşturulması gerekiyor.
- **İyimser kilitleme:** Kayıt, okunduğu sürümle birlikte değiştiriliyor. Bu arada başkası değiştirdiyse istek reddediliyor; kimse başkasının değişikliğini fark etmeden ezemiyor.
- **Veritabanı işlemi:** Hata çıkınca işlem geri alınıyor; kalıcı hale gelmemiş bir kayıt hiç var olmamış sayılıyor. Başarısız denemenin kaydı bu yüzden işlem bittikten sonra ayrıca yazılıyor.
- **Kilitlenme (deadlock):** İki işlem kaynakları farklı sırada kilitlerse birbirini sonsuza kadar bekleyebiliyor. Tek bir kilitle sıraya sokmak bunu önlüyor.
- **Sıralama kuralı (collation):** Veritabanının varsayılan kuralı yalnızca ASCII harfleri küçültüyor; "ŞAHİN" ile "şahin" eşleşmiyordu. Unicode harfleri tanıyan kural kullanıldı.
- **Kaynak verisine güvenmemek:** Bir kaynak saatini yanlış saat dilimiyle yazabiliyor; gelecekte görünen haberler bunu ortaya çıkardı.
- **Ters vekil ve istemci adresi:** Uygulamanın gördüğü adres ağ geçidinin adresi. Gerçek adres başlıkta taşınıyor; bu başlığa yalnızca güvenilen ağ geçidinden geldiğinde güvenilebiliyor.
- **Erişilebilir ad:** Ekran okuyucunun düğmeye verdiği ad testlerde de kullanılıyor.

## Takılınan yerler

- CNN Türk Türkiye saatini "GMT" diye yazıyordu; bütün haberleri 3 saat ileri kaydedilmişti ve 28 haber gelecekte görünüyordu. Kaynağa saat dilimi ayarı eklendi, eski kayıtlar bir geçiş betiğiyle düzeltildi.
- Global Voices sitesinin 40 dakikalık kesintisinde besleme 5 hatayla kendiliğinden kapandı. Elle açıldı; kendiliğinden kapanma kuralının bu kadar sert olup olmaması gözden geçirilecek.
- Metinleri Elasticsearch'e taşıyan geçişte, işçi durdurulduğu anda işlenmemiş notların metni kaybolabilirdi. Geçiş betiği metinleri notlara kendisi taşıyacak şekilde değiştirildi; veri kaybı olmadı.
- Görsel dönüştürme büyük görsellerde fazla bellek kullanıyordu; dönüştürme yöntemi değiştirildi.
- Yeniden indeksleme işinde görsel deposunun ayarları eksikti; iş ilk denemede başarısız oldu, ayarlar eklendi.