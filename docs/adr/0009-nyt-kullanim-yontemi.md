# ADR-0009: NYT API Kullanım Yöntemi

- **Durum:** Kabul edildi
- **Tarih:** 2026-11-04
- **İlişki:** ADR-0006'da doğrulanacağı belirtilen ayrıntıları belirler.

## Bağlam

ADR-0006 ile kaynak setine eklenen NYT API'nin kullanım koşulları, API anahtarı alınarak ve resmi dokümantasyon incelenerek doğrulanmıştır (04.11.2026). Bulgular:

- **İstek limitleri:** API başına günde 500, dakikada 5 istek. İstekler arasında 12 saniye beklenmesi önerilmektedir.
- **Top Stories API:** Bir bölümün ön sayfasındaki güncel haberleri döndürür; 26 bölüm ve ana sayfa (`home`) sorgulanabilir. Yanıtlar 10 dakika önbellekte tutulmaktadır.
- **Archive API:** Bir ayın bütün haberlerini tek yanıtta döndürür; alan yapısı Top Stories'ten farklıdır. Yapılan ölçümde arşivin yaklaşık 12 saat geriden geldiği görülmüştür.
- **Saklama:** Branding Guide'a göre API içeriği, servisin kullanımı bittikten sonra 24 saatten uzun süre arşivlenemez veya önbellekte tutulamaz; hesap kapatılırsa hiçbir süre tutulamaz. NYT'nin Archive dokümantasyonu, API'nin yerel bir makale meta verisi veritabanı oluşturmak için kullanılabileceğini belirtmektedir.
- **Atıf:** NYT içeriği gösteren her sayfada `https://developer.nytimes.com` adresine bağlantı veren bir NYT API logosu bulunmalıdır; logo verilen boyutlardan biri olmalı ve değiştirilmemelidir. Logonun uygun olmadığı durumlarda "Data provided by The New York Times" yazısı kullanılabilir. İçerik, başlık, bağlantı ve meta veri değiştirilemez; NYT sayfaları çerçeve içinde gösterilemez.

## Karar

1. **Düzenli toplama yalnızca Top Stories API ile yapılır.** Archive API düzenli toplamada kullanılmaz; testlerde geçmiş veri sağlamak ve gerektiğinde toplama boşluklarını doldurmak için kullanılabilir.
2. **İstek bütçesi:** Günlük limitin en fazla %80'i (400 istek) zamanlanmış toplamaya ayrılır. NYT'ye yapılan istekler arasında en az 12 saniye beklenir.
3. **Bölümler ve sıklıklar:** Hangi bölümlerin hangi sıklıkla sorgulanacağı, kategori eşleme tablosuyla birlikte bu bütçe içinde belirlenecektir. Bütün bölümler sorgulanırsa her bölüm yaklaşık 1,5 saatte bir sorgulanabilir.
4. **Saklama:** Saklama hükmü, sürenin servisin kullanımı bittiğinde başladığı şeklinde yorumlanmıştır. NYT içeriği, API kullanıldığı sürece saklanır. Kullanım bırakılırsa 24 saat içinde, hesap kapatılırsa derhal NYT içeriğinin tamamı (görseller dahil) silinir.
5. **Atıf:** NYT içeriği gösteren her ekranda NYT API logosu gösterilir. İçerik değiştirilmeden gösterilir; bağlantılar NYT'nin özgün sayfasına gider. Arama sonuçlarındaki vurgulama, içeriği değil yalnızca görünümünü değiştirdiğinden bu kurala aykırı kabul edilmez.
6. **Tekrar eden haber:** Aynı haber birden fazla bölümde yer alabilir. Haber, `uri` kimliğiyle tespit edilir; ilk kaydedilen kayıt korunur.

## Uygulama (İ-13, 24 Kasım 2026)

- **Bölümler ve sıklıklar (3. madde):** 11 bölüm okunur: world 30 dakikada bir; us, politics, business, technology, science, health, arts, movies, travel ve food saatte bir. Günde 288 istek eder; 400'lük bütçenin kalanı hata sonrası yeniden denemelere ve elle okumalara kalır (`V22`).
- **Alınmayan bölümler:** Ön denemede sports boş döndü (Nisan 2025'ten beri güncellenmiyor), books/review 401 verdi. home (karışık içerik), opinion (köşe yazısı), nyregion (New York yerel haberleri) ve kalan bölümler bütçe için alınmadı.
- **Kategori eşlemesi:** Kategori, haberin kendi bölümünden bulunur. ABD'nin iç haberleri (us, politics, nyregion) bu uygulamanın okuru için dış haber olduğundan Dünya'ya eşlenir; eşlenmeyen bölümler (opinion, magazine, podcasts gibi) Diğer'e düşer. Tablo `V22`'dedir.
- **Bütçe:** Son 24 saatteki istekler sayılır; sınıra ulaşılınca istek atılmaz (ADR-0017, 14. bölüm).
- **Atıf metni:** Kaynağın atıf metni "Data provided by The New York Times"tır (`sources.attribution_text`).

## Sonuçlar

- NYT haberlerinin tazeliği, istek limitleriyle sınırlıdır.
- Bir kaynağın bütün içeriğini silebilme işlevi gereklidir.
- NYT API logosu arayüze eklenecektir.

## Kaynaklar

- NYT Developer Portal (FAQ, Branding Guide ve API dokümantasyonu): https://developer.nytimes.com
- NYT API kullanım şartları: https://developer.nytimes.com/terms