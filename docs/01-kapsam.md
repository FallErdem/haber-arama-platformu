# Kapsam

## Amaç

Farklı haber kaynaklarından haberleri düzenli olarak toplayıp tek yerde birleştiren, aranabilir hale getiren ve sonuçları medyalarıyla birlikte, özgün habere bağlantı vererek gösteren kurum içi bir web uygulaması geliştirmek.

## Hedef Kullanıcılar

- **Kullanıcı:** Kurum içinde haberleri takip etmesi gereken ekiplerin üyeleri (örneğin kurumsal iletişim, medya takip ekipleri, sektör analistleri). Belirli konuların farklı kaynaklarda nasıl haberleştiğini izler, geçmişe dönük arama yapar, ilgilendiği haberleri kaydeder.
- **Yönetici:** Haber kaynaklarını, kullanıcıları ve rolleri yönetir; toplama işlerini, audit loglarını ve sistem durumunu izler.

## Çözülen Sorun

Haber takip eden bir çalışan, bir konuyla ilgili haberleri bulmak için çok sayıda haber sitesini tek tek ziyaret etmek zorundadır. Her sitenin arama özelliği farklıdır, geçmiş haberlere erişim zordur ve sonuçlar tek yerde karşılaştırılamaz. Bu uygulama, seçilmiş kaynaklardaki haberleri tek bir arama arayüzünde sunarak bu süreci kısaltır.

## Kapsam İçi

- Birden fazla ve farklı türde kaynaktan düzenli haber toplama
- Aynı haberin tekrarlarının tespit edilmesi
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
- Kaynakların kullanım şartlarına ve erişim kurallarına uyulur, kaynak sitelere aşırı yük bindirilmez.
- Özgün kaynak her zaman gösterilir.

## Açık Sorular

Aşağıdaki konular ilgili dokümanlarda netleştirilecektir:

- Hedef kullanıcı sayısı ve beklenen kullanım yoğunluğu (gereksinimler)
- Kullanılacak kaynakların listesi ve türleri (kaynak araştırması)
- Haberin tam metninin mi yoksa yalnızca özetinin mi saklanacağı (gereksinimler ve riskler)