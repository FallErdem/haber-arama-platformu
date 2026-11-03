# Kapsam

## Amaç

Farklı haber kaynaklarından haberleri düzenli olarak toplayıp tek yerde birleştiren, aranabilir hale getiren ve sonuçları medyalarıyla birlikte, özgün habere bağlantı vererek gösteren kurum içi bir web uygulaması geliştirmek.

## Hedef Kullanıcılar

- **Kullanıcı:** Kurum içinde haberleri takip etmesi gereken ekiplerin üyeleri (örneğin kurumsal iletişim, medya takip ekipleri, sektör analistleri). Belirli konuların farklı kaynaklarda nasıl haberleştiğini izler, geçmişe dönük arama yapar, ilgilendiği haberleri kaydeder.
- **Yönetici:** Haber kaynaklarını, kullanıcıları ve rolleri yönetir; toplama işlerini, audit loglarını ve sistem durumunu izler.
> **Not:** Uygulama eğitim amaçlıdır ve gerçekte yalnızca geliştirici tarafından kullanılacaktır. Yukarıdaki kullanıcı kitlesi, gereksinimlerin ve tasarım kapasitesinin belirlenmesinde esas alınan hedeftir (bkz. `02-gereksinimler.md`, 4.1).

## Çözülen Sorun

Haber takip eden bir çalışan, bir konuyla ilgili haberleri bulmak için çok sayıda haber sitesini tek tek ziyaret etmek zorundadır. Her sitenin arama özelliği farklıdır, geçmiş haberlere erişim zordur ve sonuçlar tek yerde karşılaştırılamaz. Bu uygulama, seçilmiş kaynaklardaki haberleri tek bir arama arayüzünde sunarak bu süreci kısaltır.

## Kapsam İçi

- Birden fazla ve farklı türde kaynaktan düzenli haber toplama
- Aynı haberin tekrarlarının tespit edilmesi
- Haberlerin ortak bir kategori listesine göre sınıflandırılması (ADR-0004)
- Toplanan haberlerde arama, filtreleme ve sayfalama
- Haber detayının ve medyalarının gösterilmesi, özgün habere bağlantı verilmesi
- Kullanıcıya özel haber kaydetme özelliği
- Yönetim paneli: kullanıcı ve rol yönetimi, kaynak yönetimi, toplama işlerinin takibi, audit log görüntüleme ve arama, sistem durumu ve temel istatistikler
- Türkçe ve İngilizce haber kaynakları

## Kapsam Dışı

- **Yerel mobil uygulama:** Web arayüzü farklı ekran boyutlarına uyumlu olacağından mobil tarayıcıdan kullanılabilir; ayrıca bir mobil uygulama geliştirilmeyecektir.
- **Kullanıcıların kaynak eklemesi:** Her kaynağın kullanım şartlarının kontrol edilmesi gerektiğinden kaynak ekleme yalnızca yöneticiler tarafından yapılır.
- **Uygulamanın herkese açılması:** Haber içerikleri telif hakkına tabi olduğundan uygulama yalnızca yetkilendirilmiş kurum içi kullanıcılara açıktır.
- **Erişimi kısıtlı içerik:** Giriş, ödeme duvarı veya bot koruması arkasındaki içerikler toplanmaz.

## Sonraki Aşama Adayları

Aşağıdakiler bu aşamada yapılmayacak, temel kapsam tamamlandıktan sonra değerlendirilecektir:

- **Yapay zekâ ile özetleme veya öneri:** Telifli içeriğin işlenmesinin hukuki boyutu ve maliyeti ayrıca değerlendirilmelidir.
- **E-posta veya anlık bildirimler:** Örneğin takip edilen bir konuda yeni haber çıktığında kullanıcıya bildirim gönderilmesi.

## Kısıtlar

- Teknolojiler: Backend Spring Boot; frontend React, TypeScript ve shadcn/ui; en az bir SQL ve bir NoSQL veritabanı; kimlik doğrulama Keycloak; çalışma ortamı Kubernetes; takip GitHub.
- Keycloak yalnızca kimlik bilgisini sağlar; yetkilendirme uygulamanın veritabanındaki kullanıcı tablosuna göre yapılır.
- Kaynakların erişim kurallarına (robots.txt, istek limitleri ve istek aralıkları) uyulur; kaynak sitelere aşırı yük bindirilmez. Bot koruması, erişim engeli veya ödeme duvarı gibi teknik korumalar aşılmaz.
- Kaynakların kullanım koşullarına uyulur. Türk haber kaynakları için şirket kararına dayanan istisna ADR-0004'tedir.
- Özgün kaynak her zaman gösterilir.

## Açık Sorular

Kapsam aşamasında açık kalan sorular aşağıdaki dokümanlarda cevaplanmıştır:

- **Hedef kullanıcı sayısı ve kullanım yoğunluğu:** Tasarım kapasitesi 500 kayıtlı ve en fazla 50 eş zamanlı kullanıcıdır (`02-gereksinimler.md`, 4.1).
- **Kullanılacak kaynakların listesi ve türleri:** ADR-0003 ve ADR-0004.
- **Haberin tam metninin mi yoksa yalnızca özetinin mi saklanacağı:** Kaynak tam metin veriyorsa tam metin, vermiyorsa özet saklanır; arama her ikisinde de yapılır (`02-gereksinimler.md`, FG-AR-01). Guardian içerikleri en fazla 24 saat saklanır (ADR-0003).