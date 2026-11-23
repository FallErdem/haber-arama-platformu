# Yedekten Geri Dönüş Denemesi (23 Kasım 2026)

İş kalemi İ-34; gereksinimler FOG-10 ve FOG-11. Yedekleme yöntemi ADR-0018'in 14. bölümündedir. Saatler Türkiye saatidir.

## Ortam

| | |
|---|---|
| Küme | Yerel k3d kümesi, tek düğüm (k3s v1.36.6) |
| PostgreSQL | 18.4 (CloudNativePG 1.30.1); `news` 28 MB (5.060 haber), `keycloak` 15 MB |
| Elasticsearch | 9.4.9, tek düğüm; 55 indeks, yaklaşık 8,5 MB |
| MinIO | Silo `RELEASE.2026-10-26T00-00-00Z`; yedekler `backups` kovasında |
| Yedeklerin boyutu | PostgreSQL dökümleri 2,4 MiB (2 dosya), Elasticsearch snapshot'ı 8,4 MiB |

## Senaryo

Canlı veriye dokunmadan, yedekler geçici kopyalara geri yüklendi ve canlı veriyle karşılaştırıldı.

1. **PostgreSQL:** `restore_check` ve `restore_check_keycloak` adlı geçici veritabanları oluşturuldu. 16:39:56'da alınan dökümler MinIO'dan okunup `pg_restore` ile bu veritabanlarına yüklendi.
2. Her tablonun satır sayısı canlı veritabanıyla karşılaştırıldı. Farklar, canlı veritabanında dökümden sonra eklenen satırların sayısıyla karşılaştırıldı.
3. **Elasticsearch:** 17:00:30'da alınan snapshot, indekslerin adları `restored-articles-...` olacak şekilde geri yüklendi. `articles` takma adı geri yüklenmedi; arama canlı indekslerde kaldı.
4. İndeks başına belge sayıları ve rastgele seçilen 50 haberin başlığı, özeti ve tam metni canlı indekslerle karşılaştırıldı.
5. Geçici veritabanları ve indeksler silindi; canlı verinin yerinde olduğu yeniden sayıldı.

## Hedef

- Geri dönüş en fazla 2 saatte tamamlanır (RTO); kaybedilen veri en fazla son 24 saattir (RPO) (FOG-10).
- Geri yüklenen veri, yedeğin alındığı ana kadar eksiksizdir.

## Sonuç

| Yedek | Geri yükleme süresi | Karşılaştırma |
|---|---|---|
| `news` dökümü | 0,5 sn | 15 tablonun 10'u aynı. Farklı 5 tablodaki farkların hepsi dökümden sonra eklenen satırlar: `articles` 29, `article_categories` 30, `media` 17, `outbox_events` 29, `ingestion_runs` 89 |
| `keycloak` dökümü | 0,5 sn | 101 tablonun 100'ü aynı. `event_entity`'deki 24 satırlık fark, dökümden sonraki oturum olayları |
| Elasticsearch snapshot'ı | 1,8 sn | 55 indeksin 54'ü aynı. `articles-g4-2026.11.01`'deki 2 belgelik fark, snapshot'tan sonra eklenen 2 haber. Örnek 50 haberin 50'sinde başlık, özet ve tam metin aynı |

- **RPO:** Yedekler günde bir kez alınır (PostgreSQL 03:00, Elasticsearch 03:30); kaybedilecek veri en fazla 24 saattir.
- **RTO:** Geri yükleme saniyeler sürdü.
- MinIO'nun Elasticsearch'le uyumu Elasticsearch'ün kendi aracıyla da denendi (`_analyze`, 50 deneme dosyası, 34,9 MB): sorun bulunmadı (`issues_detected: []`).

## Darboğaz

Bulunmadı.

## İyileştirme ve sonraki adımlar

- Bu deneme, yedeklerin okunabildiğini ve yedeğin alındığı ana kadar eksiksiz olduğunu gösterir. Canlı verinin üzerine tam geri dönüş (uygulamalar durdurularak) İ-37'de denenecek.