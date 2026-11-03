# ADR-0003: Başlangıç Haber Kaynakları

- **Durum:** Kabul edildi; ADR-0004 ile genişletildi
- **Tarih:** 2026-11-02

## Bağlam

Şartname birden fazla ve farklı türde kaynaktan düzenli veri toplanmasını; kaynakların kullanım şartlarına ve erişim kurallarına uyulmasını, giriş, ödeme duvarı veya bot korumasının aşılmamasını istemektedir. Uygulamanın Türkçe ve İngilizce kaynaklardan haber toplaması hedeflenmektedir.

Kaynak araştırmasının ayrıntıları ve değerlendirilen kaynaklar `docs/arastirma/01-haber-kaynaklari.md` dosyasındadır. Araştırma tarihinde, kullanım hakkı açık olan iki İngilizce kaynak belirlenmiştir. İncelenen Türkçe kaynakların kullanım koşulları içeriğin kopyalanmasını, saklanmasını veya başkalarına sunulmasını yazılı izne bağladığından bu aşamada uygun bir Türkçe kaynak bulunamamıştır.

## Karar

Başlangıç kaynak seti, kullanım hakkı belgelenmiş aşağıdaki kaynaklardan oluşacaktır:

| Kaynak | Tür | Dil | Kullanım hakkı |
|---|---|---|---|
| The Guardian Open Platform | API | İngilizce | Developer şartları (ticari olmayan kullanım) |
| Global Voices | RSS | İngilizce | CC BY |

Bu set, şartnamenin "birden fazla ve farklı türde kaynak" şartını karşılar. Türkçe kaynaklar, kullanım hakkı doğrulandıkça kaynak setine eklenecektir.

## Sonuçlar

- Uygulama baştan çok dilli olacak şekilde tasarlanacaktır. Her kaynağın dili kaynak tanımında tutulacak ve arama altyapısı Türkçe ile İngilizceyi destekleyecektir. Türkçe kaynak eklenmesi bir yapılandırma işlemi olacaktır.
- Guardian içerikleri en fazla 24 saat saklanabileceği için veri modeli kaynak bazında saklama süresini desteklemelidir.
- Global Voices için iki istek arasında en az 10 saniye beklenecektir; istek aralığı kaynak bazında ayarlanabilir olmalıdır.
- Kaynaklar arası format farkları nedeniyle kaynak tanımı, alanların nereden okunacağını belirten bir eşleme içermelidir.
- Kullanım hakkı doğrulanmış olan New York Times API, Eurasianet ve ProPublica, ihtiyaç halinde eklenebilecek kaynaklardır.