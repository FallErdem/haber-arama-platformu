# Güvenlik, Dayanıklılık ve Kurtarma Testleri (27 Kasım 2026)

İş kalemi İ-37; gereksinimler FOG-09, FOG-10 ve FOG-11. Testlerin tanımı `docs/08-test-stratejisi.md`'nin 7. bölümündedir. Saatler Türkiye saatidir.

## Ortam

Yerel k3d kümesi (tek düğüm), performans testleriyle aynı bilgisayar. Uygulamalar `main`'deki son kodla (piyasa verileri dahil, PR #80) çalışıyordu. Her bileşenin tek kopyası var.

## Güvenlik

**Senaryo:** Çalışan uygulamaya `curl` ile token'sız, sahte token'lı ve imzasız istekler gönderildi. Yanına her PR'da çalışan otomatik denetimler eklendi.

**Hedef:** Yetkisiz istek backend'de reddedilir; hata yanıtı iç ayrıntı vermez; yönetim adresleri dışarıya kapalıdır.

**Sonuç: Hedefler sağlandı.**

| İstek | Yanıt |
|---|---|
| Token'sız arama, yönetim (`/api/v1/admin/users`) ve piyasa verileri | 401, `application/problem+json`, kod `UNAUTHENTICATED` |
| Sahte (imzası geçersiz) token'la arama | 401 |
| İmzasız veya bozuk imzalı görsel adresi | 403 |
| `/actuator/health` ve `/actuator/prometheus` (dışarıdan) | Frontend'in sayfası döner; API'ye ulaşılmaz |

401 yanıtında güvenlik başlıkları bulunuyor: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Cache-Control: no-cache, no-store`. Gövde yalnızca durum, başlık ve hata kodunu içeriyor.

Her PR'da çalışan otomatik denetimler:

- **Yetki matrisi:** `AccessControlTests` (9 test). Onay bekleyen, reddedilmiş ve pasif kullanıcı 403 alır; yönetici olmayan yönetim adreslerine erişemez; pasif yapılan kullanıcının erişimi bir sonraki istekte kesilir.
- **Zararlı HTML:** İşçideki temizlik (`test_html_cleaner.py`, 21 test) ve frontend'deki ikinci temizlik (`sanitize.test.ts`) betik, olay özniteliği ve `javascript:` adreslerini siler.
- **Gizli bilgi ve bağımlılık açıkları:** gitleaks ve Trivy.

## Dayanıklılık

**Senaryo:** Elasticsearch ve MinIO sırayla kapatıldı (`kubectl scale ... --replicas=0`) ve yeniden açıldı. Bu sırada pod'lar, işçinin logları ve veritabanındaki bekleyen işler izlendi.

**Hedef (strateji 7.2):** Elasticsearch kapalıyken arama anlamlı bir hata döner, diğer işlevler çalışır (FOG-09), değişiklikler outbox'ta birikir ve Elasticsearch gelince aktarılır. MinIO kapalıyken görsel indirmeleri bekler ve sonra yeniden denenir.

**Sonuç: Hedefler sağlandı.**

| | Elasticsearch | MinIO |
|---|---|---|
| Kapalı kaldığı süre | 21:38 – 21:50 (yaklaşık 11,5 dakika) | 21:50 – 22:06 (yaklaşık 16 dakika) |
| İşçi | Haber toplamayı sürdürdü; "Elasticsearch'e ulaşılamadı; outbox notları bekliyor" | Haber toplamayı sürdürdü; görselli ilk haberler gelince (21:59) "Nesne depolamaya ulaşılamadı; görseller bekliyor", yaklaşık 30 saniyede bir yeniden denedi |
| Biriken iş | 37 outbox notu | 22 görsel (`PENDING`) |
| Geri gelince | Elasticsearch hazır olduktan 3 saniye sonra 37 not aktarıldı (36 haber metniyle yazıldı, hata 0) | MinIO hazır olduktan 39 saniye sonra 22 görselin hepsi ilk turda indirildi (başarısız 0); kesinti görsellerin deneme hakkından düşülmedi |
| API, işçi, frontend | Ayakta kaldı, hiçbiri yeniden başlamadı | Ayakta kaldı, hiçbiri yeniden başlamadı |

API'nin bu bileşenler kapalıyken verdiği yanıtları otomatik testler denetler (`UnavailableServicesTests`, 6 test): Elasticsearch kapalıyken arama ve haber detayı `503 SEARCH_UNAVAILABLE`, MinIO kapalıyken görsel `503 MEDIA_UNAVAILABLE` döner ve iç ayrıntı vermez; onlarla ilgisi olmayan uç noktalar ve yönetim panosu çalışır, pano ikisini kapalı gösterir.

Bir haber kaynağının bozulması işçinin testlerinde denetlenir (`test_ingestion_service.py`): besleme art arda 5 hatada kendiliğinden kapanır ve audit kaydı yazılır.

## Kurtarma

Yedekten geri dönüş 23 Kasım'da denendi (`2026-11-23-yedekten-geri-donus.md`). PostgreSQL dökümleri (`news`, `keycloak`) ve Elasticsearch snapshot'ı geçici kopyalara 0,5–1,8 saniyede geri yüklendi. Karşılaştırmada farkların hepsi yedekten sonra eklenen satırlardı; örnek 50 haberin metni birebir aynıydı. Hedefler (RTO ≤ 2 saat, RPO ≤ 24 saat) sağlandı.

## Darboğaz

Bulunmadı.

## İyileştirme

Gerekmedi. Bileşenlerin kapanmasına karşı davranış zaten tasarımın parçası: işçi Elasticsearch ve MinIO'yu beklerken işi PostgreSQL'de biriktiriyor (outbox ve görsel kuyruğu), API ise yalnızca o bileşene bağlı uç noktalarda 503 dönüyor.
