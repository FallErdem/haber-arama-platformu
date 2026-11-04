# ADR-0011: Veri Depoları, Veri Yerleşimi ve Yaşam Döngüsü

- **Durum:** Kabul edildi
- **Tarih:** 2026-11-04

## Bağlam

Şartname en az bir SQL ve bir NoSQL veritabanı kullanılmasını, bir arama özelliği sunulmasını ve verilerin zamanla sistemi yavaşlatmayacak şekilde yönetilmesini istemektedir. Hangi ürünlerin seçileceği ve hangi verinin nerede tutulacağı geliştiriciye bırakılmıştır.

04.11.2026 tarihli görüşmede şunlar belirtilmiştir:

- Elasticsearch, NoSQL veritabanı şartını karşılamaktadır.
- Haberlerin meta verisi ve verinin yaşına ilişkin bilgiler (sıcak, soğuk vb.) PostgreSQL'de tutulmalıdır.
- Görseller MinIO nesne depolamada saklanmalıdır (ADR-0010).

Arama gereksinimleri; tam metin araması, alan ağırlıklandırma, vurgulama, Türkçe ve İngilizce dil analizi ve benzer haberlerin gruplanmasıdır (FG-AR-01, FG-AR-05, FG-AR-11, FG-VT-11). Arama, en az 1 milyon haberlik veride de 500 ms hedefini karşılamalıdır (FOG-01, FOG-07).

## Değerlendirilen Seçenekler

### Arama teknolojisi

**PostgreSQL tam metin araması**

- Artı: Ek bir bileşen gerektirmez; veri tek yerde durur, eşitleme gerekmez.
- Artı: Ters indeks, Türkçe kök bulma, alan ağırlıklandırma ve vurgulama desteği vardır.
- Eksi: İlgililik sıralaması, benzer belge bulma ve yazım hatası toleransı daha sınırlıdır.
- Eksi: Arama yükü veritabanının diğer işleriyle aynı kaynakları paylaşır.

**Elasticsearch**

- Artı: Gelişmiş ilgililik sıralaması (BM25), dile özgü analiz, benzer belge bulma ve vurgulama hazır olarak sunulur.
- Artı: Arama yükü veritabanından ayrı ölçeklenir; yaşam döngüsü yönetimi (ILM) yerleşik olarak bulunur.
- Eksi: Ek bir bileşendir; daha fazla bellek tüketir ve veritabanıyla eşitlenmesi gerekir.

### Haber metninin nerede tutulacağı

**Yalnızca Elasticsearch'te**

- Artı: Metin tek yerde tutulur, depolama alanı azalır.
- Eksi: Elasticsearch asıl kayıt haline gelir; indeks bozulursa veya kaybolursa metin de kaybolur.

**Hem PostgreSQL'de hem Elasticsearch'te**

- Artı: PostgreSQL asıl kayıt olarak kalır; Elasticsearch her zaman PostgreSQL'den yeniden oluşturulabilir.
- Eksi: Metin iki kez depolanır.

### Sürümler

- **PostgreSQL 18:** Güncel kararlı sürümdür. PostgreSQL 19 karar tarihinde sürüm adayı aşamasındadır; genel kullanıma açılması 19 Kasım 2026'da planlanmaktadır ve PostgreSQL ekibi sürüm adaylarının üretimde kullanılmasını önermemektedir.
- **Elasticsearch 9.x:** Güncel ana sürümdür. Elasticsearch, 8.16.0 sürümünden itibaren AGPL dahil üç lisans seçeneğiyle dağıtılmaktadır. Yaşam döngüsü yönetimi (ILM), ücretsiz Basic aboneliğin parçasıdır.

## Karar

### Veri depolarının rolleri

| Depo | Tuttuğu veri | Rolü |
|---|---|---|
| PostgreSQL 18 | Kullanıcılar, kaynaklar ve beslemeler, haberlerin bütün bilgileri (başlık, özet, tam metin, kategoriler, yaşam döngüsü durumu), görsel kayıtları, kaydedilen haberler ve aramalar, toplama işi kayıtları, audit log | Asıl kayıt |
| Elasticsearch 9.x | Haberlerin arama için gereken alanları | Türetilmiş arama indeksi; PostgreSQL'den yeniden oluşturulabilir |
| MinIO | Görsel dosyaları | Dosya deposu; PostgreSQL'de yalnızca dosyanın anahtarı tutulur |

Kesin yama sürümleri, kurulum sırasında o tarihteki en güncel yama sürümleri olarak seçilip sabitlenecektir.

### Yaşam döngüsü

| Durum | Yaş | PostgreSQL | Elasticsearch | Aramada |
|---|---|---|---|---|
| Sıcak | 0–30 gün | Tam kayıt | Yazmaya açık güncel indeks | Varsayılan aramada |
| Ilık | 30 gün – 1 yıl | Tam kayıt | Salt okunur, birleştirilmiş aylık indeksler | Varsayılan aramada |
| Soğuk | 1 yıldan eski | Tam kayıt | Salt okunur aylık indeksler | Varsayılan aramada; sıralamada geriye düşer |

- Her haberin yaşam döngüsü durumu PostgreSQL'de tutulur. Haber tablosu aylara göre bölümlenir.
- Elasticsearch'te haberler aylık indekslerde tutulur; durum geçişleri ILM ile otomatik yapılır.
- PostgreSQL'deki durumlar, toplayıcı rolünde çalışan zamanlanmış bir işle her gün güncellenir (ADR-0005).
- Haberler hiçbir durumda silinmez; görseller her durumda MinIO'da saklanır.

## Sonuçlar

- Haber metni iki depoda tutulduğundan depolama alanı artar; bu artış veri büyümesi hesabında dikkate alınacaktır.
- PostgreSQL ile Elasticsearch'ün nasıl eşitleneceği ayrı bir kararda belirlenecektir. Tutarsızlık durumunda Elasticsearch indeksi PostgreSQL'den yeniden oluşturulabilir (R-20).
- Soğuk veri de varsayılan aramada yer aldığından her arama bütün aylık indeksleri tarar. Performans kazancı, eski indekslerin salt okunur ve birleştirilmiş olmasından ve PostgreSQL'deki aylık bölümlemeden gelir. Bunun yeterliliği hacim testinde (FOG-07) ölçülecektir; yetersiz kalırsa soğuk veri varsayılan aramanın dışına çıkarılacaktır.
- Yaşam döngüsü kuralları şirkete önerilecek; gelen geri bildirime göre güncellenebilecektir.
- Geliştirme bilgisayarında yerel olarak kurulu PostgreSQL kullanılmaz; veri depoları konteynerlerde çalıştırılır.

## Kaynaklar

- PostgreSQL 19 RC 1 duyurusu: https://www.postgresql.org/about/news/postgresql-19-rc-1-3409/
- Elastic abonelikleri: https://www.elastic.co/subscriptions
- Elastic Stack 6.6 duyurusu (ILM'nin Basic abonelikte sunulması): https://www.elastic.co/about/press/elastic-releases-elastic-stack-6-6-apm-on-elasticsearch-service-and-elastic-cloud-enterprise-2-1