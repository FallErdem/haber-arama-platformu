# ADR-0010: Görsellerin Nesne Depolamada Saklanması

- **Durum:** Kabul edildi; kurulum yöntemi ADR-0018 ile belirlendi
- **Tarih:** 2026-11-04
- **İlişki:** ADR-0004'teki görsel kuralını değiştirir.

## Bağlam

ADR-0004'te görsellerin kopyalanmaması ve kaynağın kendi adresinden gösterilmesi kararlaştırılmıştı. 04.11.2026 tarihli görüşmede, görsellerin kaynaktan indirilip yerel olarak MinIO nesne depolama sisteminde saklanmasını; ileride videoların da saklanabilmesini istemiştir.

MinIO, Amazon S3 ile uyumlu bir API sunan bir nesne depolama sistemidir. Topluluk sürümü Ekim 2025'ten itibaren hazır derlenmiş dosyalar ve konteyner imajları olmadan yalnızca kaynak kod olarak dağıtılmakta, Aralık 2025'ten itibaren bakım modunda bulunmakta ve depo Nisan 2026'da arşivlenmiştir. Şirket bu durumdan haberdardır ve MinIO'nun kullanılmasını önermektedir.

## Karar

- Haberlerin görselleri toplama sırasında kaynaktan indirilir ve MinIO'da saklanır. Arayüz, görselleri kaynağın adresinden değil, uygulamanın kendi altyapısından gösterir. Görsellerin arayüze nasıl sunulacağı mimari dokümanında belirlenecektir.
- Veritabanında her görsel için depolama anahtarı, görselin kaynaktaki adresi ve varsa atıf bilgisi (örneğin fotoğrafçı) tutulur.
- Görsel indirmeleri, kaynak düzeyindeki istek kurallarına uyar.
- İndirilemeyen görselin yerine yer tutucu gösterilir.
- Videolar şimdilik indirilmez. Veri modeli medya türünü ayırt edecek şekilde tasarlanır; videolar ileride eklenebilir.
- MinIO'nun kurulum yöntemi (kaynaktan derleme veya topluluk çatalı) dağıtım kararlarında belirlenecektir.

## Sonuçlar

- Kaynak bir görseli kaldırsa veya adresini değiştirse de görsel görüntülenmeye devam eder.
- Disk kullanımı artar; veri büyümesi hesabında medya dosyaları ayrıca hesaplanacaktır.
- Kaynakların kullanım koşullarıyla çelişki riski görselleri de kapsar; bu risk şirket tarafından kabul edilmiştir.
- Bir haberin gizlenmesi ve bir kaynağın içeriğinin silinmesi, MinIO'daki görselleri de kapsar.
- MinIO topluluk sürümü bakım modunda olduğundan güvenlik güncellemeleri sınırlıdır.
- Görseller uygulamanın kendi altyapısından sunulduğundan, güvenlik başlıklarında kaynakların alan adlarına izin verilmesi gerekmez.
- Geliştirme ortamında çalışan bileşenlere bir nesne depolama sistemi eklenir.