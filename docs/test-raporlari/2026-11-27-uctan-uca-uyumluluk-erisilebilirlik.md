# Uçtan Uca, Uyumluluk ve Erişilebilirlik Testleri (27 Kasım 2026)

İş kalemi İ-36; gereksinimler FOG-30 ve FOG-34. Testlerin tanımı `docs/08-test-stratejisi.md`'nin 5.4, 7.4 ve 7.5. bölümlerindedir.

## Ortam

Yerel k3d kümesindeki uygulama (`http://haber.localhost`), `main`'deki son kodla (PR #80). Gerçek Keycloak ve gerçek haber verisi.

## Uçtan uca ve uyumluluk

**Senaryo:** Kullanıcının asıl akışları Firefox ve Chrome'da elle denendi:

1. Keycloak ile giriş ve uygulamaya dönüş.
2. Arama ve filtreler.
3. Bir haberin detayını açma ve haberi kaydetme.
4. Yönetim → Kullanıcılar ekranı.

Ekran genişliği için Chrome'un geliştirici araçlarındaki telefon görünümünde ana sayfa ve arama sonuçları, geniş ekranda (yaklaşık 1.860 px) bütün ekranlar incelendi.

**Hedef:** Akışlar iki tarayıcıda da hatasız tamamlanır; arayüz dar ve geniş ekranda düzgün görüntülenir ve kullanılır (FOG-34).

**Sonuç: Hedefler sağlandı.** Dört akış iki tarayıcıda da sorunsuz tamamlandı; telefon görünümünde ve geniş ekranda düzen bozulmadı.

Her PR'da çalışan otomatik testler: frontend'in 238 testi (Vitest ve React Testing Library). Bileşenleri kullanıcının gördüğü rollerle ve metinlerle sınar: giriş ve oturum hataları, arama ve filtreler, sayfalama, haber detayı, kaydetme, yönetim ekranları.

## Erişilebilirlik

**Senaryo:** Yalnızca klavyeyle (Tab ve Enter) arama yapıldı ve bir haber açıldı.

**Hedef:** İşlemler fare olmadan yapılabilir (FOG-30).

**Sonuç: Hedef sağlandı.** Arama ve haber açma klavyeyle sorunsuz yapıldı.

Arayüzdeki erişilebilirlik önlemleri (kodda ve testlerde):

- Sayfanın ilk odaklanılabilir öğesi "İçeriğe geç" bağlantısıdır (`AuthenticatedApp.test.tsx`).
- Kendiliğinden dönen manşette "Durdur" düğmesi vardır; manşet dönerken ekran okuyucuya her değişiklik duyurulmaz.
- Piyasa kutusunda yükseliş ve düşüş yalnızca renk ve okla değil, ekran okuyucuya kelimeyle de bildirilir.
- Simgeli düğmelerin (tema, kaydet, paylaş) ekran okuyucunun okuduğu adları vardır; tema düğmesi açık mı kapalı mı olduğunu bildirir (`aria-pressed`).
- Koyu temanın renkleri, metin karşıtlığı WCAG AA düzeyini sağlayacak şekilde ölçülerek seçildi.
- Hareketi azaltma ayarı açık kullanıcıda manşetin kayma animasyonu ve yükleniyor animasyonları çalışmaz.

## Darboğaz

Bulunmadı.

## İyileştirme

Gerekmedi.
