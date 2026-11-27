# Performans Testleri (24–27 Kasım 2026)

İş kalemi İ-38; gereksinimler FOG-01, FOG-02, FOG-06 ve FOG-07. Testler, hedefler ve rapor şablonu `docs/08-test-stratejisi.md`'nin 6. bölümündedir. Saatler Türkiye saatidir.

## Ortam

| | |
|---|---|
| Bilgisayar | AMD Ryzen 7 250: 8 fiziksel, 16 mantıksal çekirdek (her çekirdek aynı anda iki iş yürütür); 30 GB bellek. Ölçümlerdeki "çekirdek" mantıksal çekirdektir: 1 çekirdek, bir mantıksal çekirdeğin o süre boyunca tamamen meşgul olması demektir |
| Küme | Yerel k3d kümesi, tek düğüm (k3s v1.36.6); giriş Traefik (Gateway API) |
| API | Spring Boot 4.1.2, Java 25; 1 kopya (ölçeklenebilirlik testinde 1 ve 2); bellek sınırı 768 MiB, CPU sınırı yok |
| Elasticsearch | 9.4.9, tek düğüm; 1 GB heap, 2 GiB bellek sınırı; 76 shard (aylık indeksler, deneme verisinin tarihlerine yayılıyor) |
| PostgreSQL | 18.4 (CloudNativePG 1.30.1); bellek sınırı 1 GiB |
| Veri hacmi | 1.009.606 haber (1 milyonu üretilmiş deneme verisi, `DENEME` kaynağında; yaklaşık 9.600'ü gerçek), 10 milyon audit kaydı (`deploy/README.md`, 14. adım) |
| Yük aracı | k6 2.3.0 (`grafana/k6:2.3.0`), Docker'da 2 çekirdek ve 1 GB bellekle sınırlı |

**Güç durumu:** 24 Kasım akşamki testler bilgisayar pildeyken çalıştı; pilde işlemci yavaşlatılır. 26 Kasım'daki testler şarjdayken ("balanced" güç profili) çalıştı. Aynı senaryoda süreler pilde belirgin biçimde uzundu; bu yüzden yük ve ani yük testleri 26 Kasım'da şarjda tekrarlandı ve iki ölçüm de aşağıda verildi.

**Sınırlama (R-25):** Yük aracı ile sistem aynı bilgisayarda çalışır. Yük aracının kaynakları Docker ile ayrıldı; yine de sonuçlar mutlak kapasite olarak değil, hedeflerle ve birbirleriyle karşılaştırmalı okunmalıdır. Hiçbir bileşende CPU sınırı yoktur (yalnızca ölçeklenebilirlik testinde API'ye geçici olarak konuldu); bileşenler bilgisayarın 16 çekirdeğini paylaşır.

## Senaryo

Bütün testler aynı kullanıcı davranışını kullanır (`tests/performance/scenario.js`); yalnızca kullanıcı sayısı ve süre değişir.

- **İşlemler:** %70 arama, %20 haber detayı, %10 kaydetme ve kaydedilenler; işlemler arasında 3–5 saniye.
  - Aramaların %80'i gerçek haberlerde sık geçen kelimelerle (Türkçe ve İngilizce, 40 kelime), %20'si kelimesizdir. Bir kısmında kategori (%30), dil (%20), son 7 gün (%10) süzgeci ve ikinci, üçüncü sayfa (%20) vardır.
  - Sonuç sayfasının ilk 8 haberinin görseli ve detay sayfasının ana görseli istenir. Tarayıcı görselleri önbelleğe aldığı için her sanal kullanıcı aynı görseli bir kez ister.
- **Kimlik:** Keycloak'ta geçici bir test client'ı (`haber-loadtest`, yalnızca şifreyle doğrudan token) ve 10 test kullanıcısı oluşturuldu (`tests/performance/setup.sh`); frontend client'ına dokunulmadı. Sanal kullanıcılar 10 hesabı paylaşır, token'ı 4 dakikada bir yeniler. k6 başlamadan her hesabın onaylı (`ACTIVE`) olduğunu denetler.
- **Ölçüm:** İstemci tarafı süreler ve hatalar k6'dan; sunucu tarafı süreler, CPU ve bellek Prometheus'tan (`tests/performance/prometheus_summary.py`); dakika dakika dökümler k6'nın zaman serisinden (`tests/performance/points_summary.py`).
- **İsteklerin yolu:** İlk iki test (yük, ani yükün 1. denemesi) bilgisayarın 80 portundan, yani k3d'nin yük dengeleyicisi (`k3d-haber-serverlb`) üzerinden Traefik'e gitti. Ani yükün 1. denemesinde bu dengeleyici tıkandığı için sonraki testler doğrudan küme düğümüne, Traefik'e gönderildi (bkz. Ani yük).

## Yük ve hacim

**Senaryo:** 50 eş zamanlı kullanıcı, 15 dakika (1 dakika artış, 30 saniye iniş); 1.009.606 haberlik indeksle. İki kez çalıştırıldı: 24 Kasım 21:09–21:26 (pilde, k3d dengeleyicisi üzerinden) ve 26 Kasım 10:49–11:06 (şarjda, doğrudan Traefik'e).

**Hedef:** Arama p95 ≤ 500 ms, p99 ≤ 1000 ms; hata oranı < %1 (FOG-01, FOG-02). 1 milyon haberle arama p95 ≤ 500 ms (FOG-07).

**Sonuç: Hedefler iki ölçümde de sağlandı.**

| Ölçüm (k6, istemci tarafı) | 26 Kasım (şarjda) | 24 Kasım (pilde) | Hedef |
|---|---|---|---|
| Arama p95 / p99 | 63 ms / 93 ms | 169 ms / 216 ms | 500 ms / 1000 ms |
| Arama ortalama / en uzun | 28 ms / 205 ms | 79 ms / 278 ms | |
| Haber detayı p95 | 14 ms | 26 ms | |
| Görsel p95 | 4 ms | 7 ms | |
| Kaydetme ve kaydedilenler p95 | 8 ms | 10 ms | |
| Hata oranı | %0 (24.403 istekten 0) | %0 (18.184 istekten 0) | < %1 |
| İstek hızı | 24,6 istek/sn (11,9 işlem/sn) | 18,3 istek/sn (11,7 işlem/sn) | |

Sunucu tarafında (Prometheus, 15 dakikalık sabit yük) arama p95 şarjda 62 ms, pilde 169 ms; istemci tarafıyla neredeyse aynı, yani Traefik ve ağın payı küçüktür. API hiç 5xx yanıt vermedi.

| Bileşen | CPU ortalama: şarjda / pilde | Bellek ortalama (sınır) |
|---|---|---|
| Elasticsearch | 1,3 / 3,5 çekirdek | 1,8–1,9 GB (2 GiB) |
| API | 0,14 / 0,19 çekirdek | 377–404 MB (768 MiB); JVM heap ~43–45 MB |
| PostgreSQL | 0,06 / 0,10 çekirdek | 301–327 MB (1 GiB) |

Pilde işlemci yavaşlatıldığı için aynı iş daha fazla işlemci zamanı tuttu; Elasticsearch'ün CPU kullanımı ve arama süreleri pilde yaklaşık 2,5 kat yüksekti.

**Darboğaz:** Arama isteklerinin süresinin ve CPU'nun büyük kısmı Elasticsearch'tedir. Arama `articles` takma adının arkasındaki bütün aylık indekslere gider; 1 milyon haber 76 shard'a dağılmış durumda. API ve PostgreSQL bu yükte neredeyse boştur. Bağlantı havuzunda (10 bağlantı) bekleyen istek görülmedi.

**İyileştirme:** Hedefler sağlandığı için bu testte değişiklik yapılmadı. Hacim arttıkça ilk bakılacak yer shard sayısıdır: eski aylık indekslerin birleştirilmesi (yıllık indeks ya da `_shrink`) her aramanın dokunduğu shard sayısını azaltır.

Hacim verisiyle yapılan çalışmada (İ-35) iki sorun daha bulunup düzeltilmişti; ikisi de küçük veride görünmüyordu:
- Audit araması tarih sınırı verilmediğinde 10 milyon kaydın bütün aylık bölümlerini tarıyordu; arama artık bölümleri iki tarih sınırına göre atlıyor.
- Outbox aktarımı işlenmiş notlar biriktikçe yavaşlıyordu (dakikada 114.600 nottan 11.000'e); bekleyen notlar için kısmi indeks eklendi (`V18`).

## Ani yük

**Senaryo:** 1 dakika 50 kullanıcı; 10 saniyede 200 kullanıcıya çıkış, 2 dakika 200 kullanıcı; 10 saniyede 50'ye iniş ve 2 dakika 50 kullanıcı.

**Hedef:** Ani yük sırasında hata oranı < %5; yük düştükten sonra 1 dakika içinde yük testi hedeflerine dönülür.

**Sonuç: Hedefler sağlandı.** Test iki kez çalıştırıldı.

| | 1. deneme (k3d dengeleyicisi üzerinden) | 2. deneme (doğrudan Traefik'e) |
|---|---|---|
| Zaman | 24 Kasım 21:28–21:34 | 24 Kasım 21:34–21:40 |
| Hata oranı | %1,96 (17.780 istekten 350) | %0 (17.676 istekten 0) |
| Arama p95 / p99 | 227 ms / 308 ms | 219 ms / 325 ms |
| İstek hızı | 53 istek/sn | 53 istek/sn |

2. denemenin dakika dakika dökümü (arama p95): 50 kullanıcıda 190 ms; ani yük sırasında 222 ve 263 ms; yük düştükten sonraki ilk dakikada 190 ms, sonra 183 ve 180 ms. Sistem yük testi hedeflerinin dışına hiç çıkmadı.

**Darboğaz (1. deneme):** Hatalar yalnızca yükün tepe noktasındaki üç dakikada görüldü (%0,8, %3,8, %2,0) ve yük düşünce sıfırlandı. Nedeni uygulama değil, k3d'nin geliştirme ortamı için kurduğu yük dengeleyicisiydi. Dengeleyicinin logunda `socket() failed (24: No file descriptors available)` hataları vardı: nginx süreçleri en çok 1.024 dosya tanıtıcısı açabiliyor (yumuşak sınır) ve her bağlantı iki tanıtıcı tutuyor (istemci ve arka taraf). 200 kullanıcının aynı anda istediği görseller bu sınırı aştı. Aynı dengeleyici Kubernetes API sunucusunun önünde de durduğu için bu sırada `kubectl` de bağlanamadı.

**İyileştirme:** k6 istekleri doğrudan küme düğümüne gönderecek şekilde değiştirildi (`tests/performance/run.sh`); 2. denemede hiç hata kalmadı. k3d dengeleyicisi yalnızca yerel geliştirme kolaylığıdır; gerçek bir ortamda onun yerinde beklenen bağlantı sayısına göre ayarlanmış bir yük dengeleyici olur.

## Stres

**Senaryo:** 50 kullanıcıdan başlayıp her 2 dakikada 25 kullanıcı artırılır, 300 kullanıcıya kadar (23 dakika). Hata oranı %5'i veya arama p95'i 2 saniyeyi aşınca test kendiliğinden durur. Doğrudan Traefik'e; bilgisayar şarjda. 26 Kasım 09:10–09:33.

**Hedef:** Hedef değil, gözlem: kırılma noktası kaydedilir; kırıldığında sistemin çökmemesi ve yük düşünce toparlanması beklenir.

**Sonuç: Sistem 300 kullanıcıda kırılmadı.** Durdurma koşullarından hiçbiri oluşmadı; test planlanan sonuna kadar sürdü.

| Ölçüm | Değer |
|---|---|
| Hata oranı | %0 (83.580 istekten 0) |
| Arama p95 / p99 / en uzun | 64 ms / 96 ms / 376 ms |
| Haber detayı p95, görsel p95 | 12 ms, 4 ms |
| İstek hızı | ortalama 60 istek/sn; 300 kullanıcıda dakikada ~6.400 istek (~106 istek/sn) |

Dakika dakika arama p95'i, kullanıcı sayısı 6 katına çıkarken 50–55 ms'den 65–74 ms'ye yükseldi; artış yavaş ve düzenliydi. Kaynak kullanımı (Prometheus): Elasticsearch ortalama 3,6, en çok 7,0 çekirdek; API 0,24 çekirdek; PostgreSQL 0,13 çekirdek.

**Darboğaz:** Kırılma görülmedi; yükün arttığı yer yine Elasticsearch'tür. 300 kullanıcıda bilgisayarın 16 çekirdeğinin yarısından azı kullanıldı. Kırılma noktası, bu senaryoyla (işlemler arasında 3–5 saniye) 300 kullanıcının üzerindedir. Kapasitenin sınırı ölçeklenebilirlik testinde, düşünme süresi olmadan arandı.

## Ölçeklenebilirlik

**Senaryo:** Düşünme süresi olmadan, saniyedeki işlem sayısı adım adım artırılır; arama p95'i 500 ms'yi ya da hata oranı %1'i aşınca test durur. Durmadan önceki son hız, o kopya sayısında yük hedeflerini sağlayan en yüksek hızdır. Aynı test API'nin 1 ve 2 kopyasıyla çalıştırılır. Bileşenlerde CPU sınırı olmadığı için, API'nin bir darboğaz olabilmesi amacıyla yalnızca bu testte API'ye geçici CPU sınırı konuldu. Doğrudan Traefik'e; şarjda. 26 Kasım 09:34–10:48.

**Hedef:** 2 kopyada kapasite, 1 kopyaya göre en az %70 fazla (FOG-06).

**Sonuç: Hedef sağlanamadı; kapasiteyi API değil Elasticsearch belirliyor.**

| Deneme | API | Sonuç |
|---|---|---|
| A | 1 kopya, 1 çekirdek sınırı; hız her dakika 5 artar, en çok 85 işlem/sn | Sınıra ulaşılmadı. 85 işlem/sn'de arama p95 ~68 ms; API 1 çekirdeğin yalnızca 0,28'ini, Elasticsearch 6–7,6 çekirdek kullandı. API doymadığı için iki kopyayı karşılaştırmak anlamsızdı |
| B | 1 kopya, 0,25 çekirdek sınırı | 30 saniyede durdu: arama p95 10 saniye. Ölçülen kapasite değil soğuk başlangıçtı: yeni açılan API'nin Java derlemesi (JIT) 0,25 çekirdekte çok yavaş ilerledi, CPU zamanın %98'inde kısıldı, hazır olma ve canlılık kontrolleri başarısız oldu ve Kubernetes kapsayıcıyı yeniden başlattı |
| C | 1 kopya, 0,5 çekirdek sınırı; 3 dakika ısınma, sonra hız her dakika 10 artar | Hedefleri sağlayan en yüksek hız **~150 işlem/sn** (dakikada ~10.000 istek; arama p95 156 ms). |
| D | 2 kopya, her biri 0,5 çekirdek; C ile aynı | Hedefleri sağlayan en yüksek hız **~160 işlem/sn** (dakikada ~10.650 istek; arama p95 308 ms). |

İki kopyada kapasite yalnızca yaklaşık %6–7 arttı; hata oranı bütün denemelerde %0'dı.

**Darboğaz:** Elasticsearch son dakikalarda bilgisayarın işlemcisinin neredeyse tamamını kullandı (ortalama 15 çekirdek; bilgisayarda 16 mantıksal çekirdek var), API kopyaları 0,3–0,7 çekirdekte kaldı; kapasiteyi API değil Elasticsearch belirliyor.

## Uzun süre

**Senaryo:** 50 eş zamanlı kullanıcı, 2 saat (`DURATION_MINUTES=120`); yük testiyle aynı kullanıcı davranışı ve aynı 1 milyon haberlik indeks. Doğrudan Traefik'e. 27 Kasım 00:07–02:07. PostgreSQL bağlantıları test boyunca 5 dakikada bir `pg_stat_activity`'den sayıldı (26 ölçüm).

Strateji dokümanında süre 4 saatti; test 2 saat çalıştırıldı. API, Elasticsearch ve PostgreSQL'in belleği ilk 15 dakikadan sonra düz kaldığı için 2 saat bu bileşenlerde sızıntıyı görmeye yetti. Keycloak ve işçide yavaş bir artış var (aşağıda); bunların nerede dengelendiğini 4 saatlik bir test daha net gösterirdi.

**Hedef:** Son saatte bellek kullanımı ve veritabanı bağlantı sayısı ilk saate göre %10'dan fazla artmaz; hata oranı < %1. Yük testinin hedefleri de geçerlidir (arama p95 ≤ 500 ms, p99 ≤ 1000 ms).

**Sonuç: Hedefler sağlandı; bellek veya bağlantı sızıntısı görülmedi.**

| Ölçüm (k6, istemci tarafı) | 1. saat | 2. saat | Bütün test |
|---|---|---|---|
| Arama p95 / p99 | 67 ms / 99 ms | 67 ms / 98 ms | 67 ms / 98 ms |
| Arama ortalama | 30 ms | 30 ms | 30 ms (en uzun 741 ms) |
| Hata | 73.339 istekten 0 | 67.933 istekten 0 | %0 (141.272 istekten 0) |
| İşlem (kullanıcı döngüsü) | 44.647 | 44.810 | 89.457 (12,4 işlem/sn) |

Bütün testte haber detayı p95 17 ms, görsel p95 3 ms, kaydetme ve kaydedilenler p95 13 ms; istek hızı 19,6 istek/sn.

- **Dakika dakika:** İlk dakikada, kullanıcılar bağlanırken arama p95'i 635 ms'ydi (en uzun istek de bu dakikada). Sonraki 120 dakikanın hepsinde 55–79 ms arasında kaldı.
- **İkinci saatteki daha az istek:** İkinci saatte 5.400 istek daha az var; farkın tamamı görsel isteklerindedir (27.873'ten 22.422'ye). Her sanal kullanıcı bir görseli tarayıcı önbelleği gibi yalnızca bir kez ister; saatler geçtikçe görülmüş görsel sayısı artar. İşlem, arama, detay ve kaydetme sayıları iki saatte aynıdır, yani sistem yavaşlamadı.

Bellek (Prometheus, working set, saatlik ortalama):

| Bileşen | 1. saat | 2. saat | Değişim |
|---|---|---|---|
| API | 445 MB | 448 MB | +%0,8 |
| Elasticsearch | 1.814 MB | 1.808 MB | −%0,3 |
| PostgreSQL | 320 MB | 319 MB | −%0,2 |
| MinIO | 362 MB | 342 MB | −%5,8 |
| Keycloak | 687 MB | 722 MB | +%5,0 |
| İşçi | 570 MB | 601 MB | +%5,5 |

- **API:** Belleği 15 dakikalık aralıklarla 393 MB (başlangıç), 445, 447, 446, 448, 447, 447, 449 ve 448 MB: ilk 15 dakikada ısınıp sonra sabit kaldı. JVM heap çöp toplayıcıya göre 50–66 MB arasında gidip geliyor, artış eğilimi yok (başta 65, sonda 56 MB). Thread sayısı 15. dakikadan sonra 85'te sabit.
- **Keycloak:** 602 MB'tan 726 MB'a çıktı; artış giderek yavaşladı (son yarım saatte 2 MB). Kullanıcılar token'ı 4 dakikada bir yenilediği için Keycloak sürekli oturum işler.
- **İşçi:** 542 MB'tan en çok 617 MB'a çıktı (sınır 640 MiB). İşçi isteklerin yolunda değildir ve aynı büyüme yük olmadan da görülüyordu (bkz. aşağıdaki bölüm).

Bağlantılar:

- **API:** PostgreSQL bağlantıları (`news_app`) 26 ölçümün hepsinde 10'du (bağlantı havuzunun boyu); ilk ve son saat arasında fark yok. Havuzda bekleyen istek hiç olmadı (Hikari: bekleyen 0, etkin ortalama 0,05).
- **Keycloak:** Bağlantıları başta 10'du, ilk 10 dakikada 2–3'e indi ve öyle kaldı.
- **İşçi:** Bağlantıyı iş başına açıp kapattığı için ölçümlerin çoğunda görünmez (en çok 7).

Sunucu tarafında arama p95 66 ms, p99 99 ms; API hiç 5xx yanıt vermedi. Kaynak kullanımı: Elasticsearch ortalama 1,35 (en çok 1,6) çekirdek, API 0,08, PostgreSQL 0,06 çekirdek.

**Darboğaz:** Görülmedi.

**İyileştirme:** Gerekmedi. İşçinin belleğindeki artış ayrıca ele alındı (aşağıda).

## Testler sırasında bulunan diğer sorun: işçinin belleği

Yük testi sırasında işçi (Python) 64 dakikada 6 kez bellek sınırına takılıp öldürüldü (`OOMKilled`, sınır 384 MiB); her seferinde birkaç dakika ayakta kalıyordu. İşçi API'nin yolunda olmadığı için test sonuçlarını etkilemedi, ama bu sürede haber toplama ve görsel indirme kesildi. İşçinin boştaki kullanımı sınıra çok yakındı (350–380 MB); sorun NYT eklendikten sonra, NYT'nin büyük (2048 piksel) görselleri indirilirken başladı. Testler sırasında sınır kümede geçici olarak 768 MiB'a çıkarıldı; işçi o andan sonra 35 saat boyunca hiç yeniden başlamadı.

Sınır sonra dosyada 640 MiB yapıldı. Uzun süre testinde işçi 617 MB'a kadar çıktı; 27 Kasım'da 638 MiB'a ulaşıp yeniden başladı. İşçinin kullanımı zamanla sınıra doğru büyüdüğü için sınır 27 Kasım'da 1 GiB'a çıkarıldı (`deploy/k8s/base/worker/deployment.yaml`). Büyümenin nedeni ayrıca incelenmeli.
