# Hafta 1 İlerleme Notu (2–6 Kasım 2026)

## Yapılanlar

- Geliştirme ortamı kuruldu; depo, commit standardı ve GitHub üzerinden iş takibi (etiketler, pano, kilometre taşı, PR şablonu) hazırlandı.
- Analiz ve tasarım dokümanları yazıldı: kapsam, gereksinimler, risk kaydı, haber kaynakları araştırması, mimari, veri modeli, API sözleşmesi ve ekran akışları.
- NYT API anahtarı alındı; NYT ve Türk haber sitelerinin istek limitleri, kullanım şartları ve atıf kuralları resmi kaynaklardan doğrulandı.
- 17 karar ADR olarak kayda geçirildi.

## Alınan kararlar

- **Kaynaklar:** TRT Haber, NTV, CNN Türk, Global Voices (RSS/Atom) ve NYT (API). Guardian, 24 saat saklama kuralı nedeniyle NYT ile değiştirildi (ADR-0004, ADR-0006, ADR-0009).
- **Mimari:** Modüler monolit Spring Boot API ve bütün arka plan işlerini yürüten tek kopyalı Python işçisi. İki uygulama yalnızca veri depoları üzerinden iletişim kurar (ADR-0005, ADR-0017).
- **Teknolojiler:** Java 25, Spring Boot 4.1, Maven, Python 3.14, PostgreSQL 18, Elasticsearch 9, MinIO (ADR-0007, ADR-0011, ADR-0017).
- **Veri:** PostgreSQL asıl kayıt, Elasticsearch türetilmiş arama indeksi; ikisi outbox deseniyle eşitlenir. Haberler sıcak, ılık ve soğuk olarak yaşam döngüsüne tabi; hiçbiri silinmez (ADR-0011, ADR-0012, ADR-0015).
- **Kimlik ve yetki:** Keycloak yalnızca kimliği doğrular; yetki her istekte kullanıcı tablosundan kontrol edilir (ADR-0014).
- **Audit log:** Yalnızca ekleme ve okuma yetkisi, güncellemeyi ve silmeyi reddeden tetikleyici, aylık bölümleme (ADR-0016).
- **Çalışma düzeni:** GitHub Flow, merge commit, GitHub Actions (ADR-0008).

## Öğrenilenler

- Resmi kaynaktan doğrulamanın önemi.
- Kaynakların kullanım şartları mimari kararlara dönüşebiliyor.
- Elasticsearch'te salt okunur indeksten belge silinemiyor; yaşam döngüsü yönetimi indeksin yaşını varsayılan olarak oluşturulma zamanından hesaplıyor.
- Türkçe yerel ayarda Java'nın ve Python'un harf dönüşümleri hatalı sonuç verebiliyor ("I" ve "İ").
- HTML'deki `<img>` etiketi token gönderemediği için görseller imzalı adreslerle sunulmalı.
- **MinIO:** Amazon S3 ile aynı API'yi sunan bir nesne depolama sistemi. Görseller gibi dosyalar veritabanında değil, MinIO'da tutuluyor; veritabanında yalnızca dosyanın anahtarı duruyor.
- **RSS ve Atom:** Sitelerin yeni içeriklerini makinelerin okuyabileceği biçimde yayımladığı XML formatları. İkisi aynı amaca hizmet ediyor ama alan adları farklı; kaynaklar standart dışı alanlar da kullanabiliyor (TRT'nin görsel alanı gibi).
- **Elasticsearch ve ters indeks:** Her kelime kökü için o kökün geçtiği belgelerin listesi önceden hazırlanıyor; arama, belgeleri tek tek okumadan bu dizinden yapılıyor. Türkçe analizör kelimelerin eklerini atarak "derbiler" aramasının "derbide" geçen haberi bulmasını sağlıyor.
- **Outbox deseni:** Bir değişiklik ile "bu değişikliği başka sisteme aktar" kaydı aynı veritabanı işleminde yazılıyor; aktarım ayrı bir işle yapılıyor. Böylece hedef sistem çalışmasa da hiçbir değişiklik kaybolmuyor.
- **İyimser kilitleme:** Kayda bir sürüm numarası eklenip güncellemede kontrol ediliyor; eski sürüm üzerinden yapılan güncelleme reddediliyor. İki yöneticinin aynı kaydı düzenlerken birbirinin değişikliğini sessizce silmesini önlüyor.
- **Kilit dosyası:** Her paketin, dolaylı bağımlılıklar dahil, tam sürümünü ve özetini kaydediyor. venv yalnızca yalıtım sağlıyor; kilit dosyası herkesin birebir aynı paketleri kurmasını sağlıyor.

## Takılınan yerler

- Analiz ve tasarım haftanın tamamını aldı; henüz çalışan kod yok. Gelecek hafta çalışan iskelete geçilecek.
- Arka plan işleri Python'a taşındı; mimari, veri modeli ve ilgili ADR'ler güncellendi.
- GitHub Free planında özel depoda dal koruma kuralları kullanılamıyor; `main`'e yapılan her gönderimde CI'ın çalışmasıyla telafi edilecek.