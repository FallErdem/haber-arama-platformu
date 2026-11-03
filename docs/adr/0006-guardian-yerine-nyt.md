# ADR-0006: Guardian'ın Çıkarılması ve New York Times API'nin Eklenmesi

- **Durum:** Kabul edildi
- **Tarih:** 2026-11-03
- **İlişki:** ADR-0003 ve ADR-0004'teki Guardian ile ilgili kararları geçersiz kılar.

## Bağlam

Guardian Open Platform, ADR-0003'te şartnamenin "farklı türde kaynak" şartını karşılayan tek API kaynağı olarak seçilmişti. Guardian'ın kullanım şartları içeriğin en fazla 24 saat saklanmasına izin vermektedir. Bu kural; süresi dolan içeriğin silinmesini veya yenilenmesini ve kaynak bazında farklı saklama sürelerinin yönetilmesini gerektirmekte, ayrıca Guardian haberlerinde geçmişe dönük aramayı engellemektedir.

Guardian'ın yerine saklama kısıtı getirmeyen bir API aranmıştır. Değerlendirilen adaylar:

- **New York Times Developer API:** Yayıncının resmi API'sidir. NYT'nin kendi API tanımında, Archive API'nin yerel bir makale meta verisi veritabanı oluşturmak için kullanılabileceği belirtilmektedir. Tam metin vermez; başlık, özet, giriş paragrafı, bölüm, yayın tarihi ve görsel bağlantıları verir.
- **CollectAPI:** Türkçe haber veren bir API'dir; ancak bir haber toplayıcısıdır ve içeriği büyük ölçüde kaynak setindeki Türk kaynaklarının haberlerinden oluşmaktadır.

## Karar

Guardian kaynak setinden çıkarılır. Yerine **New York Times Developer API** eklenir.

- **Dil:** İngilizce.
- **Toplama:** Son haberleri bölüm bazında veren uç nokta kullanılır. Kullanılacak NYT API'leri, istek limitleri ve kullanım şartları API anahtarı alınırken resmi dokümantasyondan doğrulanacaktır.
- **Saklama:** Haberler diğer kaynaklarda olduğu gibi süresiz saklanır.
- **Kategori eşlemesi:** Haber düzeyinde, haberin bölüm bilgisine göre yapılır. Eşleme tablosu API anahtarı alındıktan sonra hazırlanacaktır.
- **İçerik:** Tam metin gelmez; arama ve gösterim başlık, özet ve giriş paragrafı üzerinden yapılır.

CollectAPI ileride ikinci bir API kaynağı olarak değerlendirilebilir.

## Sonuçlar

- Bütün kaynakların haberleri süresiz saklanır. Kaynak bazında saklama süresi tanımlama ve süresi dolan içeriği silme ihtiyacı ortadan kalkar.
- Guardian'ın 24 saat kuralından doğan risk kapanır.
- Şartnamenin "farklı türde kaynak" şartı, RSS/Atom beslemeleri ve NYT API ile karşılanır.
- NYT tam metin vermediğinden, İngilizce tam metin yalnızca Global Voices'tan gelir.
- NYT'nin istek limitlerine uyulur. Zamanlanmış işler, tek kopya çalışan toplayıcı rolünde yürütülür (ADR-0005).