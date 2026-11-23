# ADR-0008: Çalışma Düzeni — Dal Stratejisi, Kod İnceleme, CI ve İş Takibi

- **Durum:** Kabul edildi
- **Tarih:** 2026-11-03

## Bağlam

Şartname, ilerlemenin GitHub üzerinden takip edilmesini; sektörde kullanılan commit, dal ve kod inceleme standartlarından birinin seçilerek uygulanmasını; işlerin durumunun GitHub üzerinden görülebilmesini ve otomatikleştirilebilen testlerin her değişiklikte çalıştırılmasını istemektedir. Commit standardı ADR-0002'de belirlenmiştir.

Bu kararı etkileyen koşullar:

- Proje tek geliştirici tarafından yürütülmektedir.
- Depo, GitHub Free planındaki bir kişisel hesapta özel (private) olarak tutulmaktadır. GitHub'ın dal koruma kuralları (rulesets), Free planda yalnızca açık (public) depolarda kullanılabilmekte; özel depolarda GitHub Pro, Team veya Enterprise Cloud planı gerektirmektedir.
- Depo monorepo yapısındadır (ADR-0001).

## Değerlendirilen Seçenekler

### Dal stratejisi

**GitHub Flow:** Tek kalıcı dal (`main`) bulunur; her iş için kısa ömürlü bir dal açılır ve iş bitince pull request (PR) ile `main`'e birleştirilir.

- Artı: Öğrenmesi ve uygulaması kolaydır; `main` her zaman çalışır durumda tutulur.
- Artı: Her iş GitHub'da bir PR olarak görünür; CI kontrolleri PR üzerinde çalışır.
- Eksi: Aynı anda birden fazla sürümün desteklenmesi gereken projeler için yetersizdir.

**Git Flow:** Birden fazla kalıcı dal (`main`, `develop`) ve bunlara ek `feature/`, `release/`, `hotfix/` dalları bulunur.

- Artı: Planlı sürüm yayımlayan projelerde düzen sağlar.
- Eksi: Tek geliştiricili ve sürekli geliştirilen bir web uygulaması için gereğinden karmaşıktır.

**Trunk-based development:** Değişiklikler doğrudan `main`'e veya çok kısa ömürlü dallarla yapılır; tamamlanmamış özellikler özellik bayraklarıyla gizlenir.

- Artı: Çok sık entegrasyon sağlar, birleştirme çakışmalarını azaltır.
- Eksi: Güçlü bir otomatik test altyapısı ve özellik bayrağı altyapısı gerektirir.
- Eksi: Tek geliştiricide pratikte doğrudan `main`'e commit etmeye dönüşür; işlerin GitHub'daki izi zayıflar.

### Birleştirme yöntemi

**Merge commit:** Daldaki commit'ler olduğu gibi korunur ve bir birleştirme commit'i eklenir.

- Artı: Her commit tarihiyle korunur; hangi commit'lerin hangi PR'a ait olduğu görülebilir.
- Eksi: Geçmişte birleştirme commit'leri yer alır; geçmiş düz bir çizgi değildir.

**Squash:** Daldaki tüm commit'ler tek bir commit'e sıkıştırılır.

- Artı: `main` geçmişi PR başına tek commit içerir, sade görünür.
- Eksi: Dalda yapılan düzenli çalışma `main` geçmişinde görünmez hale gelir.

**Rebase:** Daldaki commit'ler `main`'in ucuna yeniden yazılır.

- Artı: Commit'ler korunur ve geçmiş düz bir çizgi olur.
- Eksi: Commit geçmişi yeniden yazıldığından, kullanımı daha fazla dikkat gerektirir.

### CI platformu

**GitHub Actions:** GitHub'ın depoyla entegre CI sistemidir; Free planda belirli bir kullanım süresi ücretsizdir.

- Artı: Ek kurulum gerektirmez; kontrol sonuçları doğrudan PR'larda görünür.
- Eksi: Özel depolarda aylık kullanım süresi sınırlıdır.

**Jenkins:** Kendi sunucusunda kurulup işletilen bir CI aracıdır.

- Artı: Esnektir ve kullanım süresi sınırı yoktur.
- Eksi: Ayrı bir sunucunun kurulup işletilmesini gerektirir.

## Karar

### Dal stratejisi

- **GitHub Flow** uygulanacaktır.
- Dal adları `<tür>/<issue-no>-<kısa-açıklama>` biçiminde olacaktır (örnek: `feat/12-haber-arama`). Tür, ADR-0002'deki commit türlerinden biridir. Dal adlarında küçük harf ve tire kullanılır, Türkçe karakter kullanılmaz.
- Kod değişiklikleri bir dalda yapılır ve PR ile `main`'e birleştirilir.
- Doküman değişiklikleri doğrudan `main`'e commit edilebilir. Bir kod değişikliğine bağlı doküman güncellemeleri, kodla aynı PR'da yapılır.

### Kod inceleme ve birleştirme

- GitHub, PR'ı açan kişinin kendi PR'ını onaylamasına izin vermediğinden PR'lar için onay şartı aranmaz.
- Her PR'a otomatik olarak eklenen bir şablon bulunur. Şablondaki kontrol listesi PR birleştirilmeden önce tamamlanır:
  - Değişikliklerin tamamı birleştirmeden önce gözden geçirildi.
  - İlgili testler eklendi veya güncellendi ve CI kontrolleri geçti.
  - Değişiklikler gizli bilgi (parola, token, API anahtarı) içermiyor.
  - İlgili dokümanlar güncellendi.
  - PR açıklamasında ilgili issue (`Closes #n`) ve varsa gereksinim kimlikleri belirtildi.
- Birleştirme yöntemi olarak **merge commit** kullanılır.
- Dal, PR birleştirildikten sonra silinir.

### CI

- CI platformu olarak **GitHub Actions** kullanılacaktır.
- CI; her PR'da ve `main` dalına yapılan her gönderimde çalışır.
- Yapılacak kontroller:

| Kontrol | Dayanak | Çalışma koşulu |
|---|---|---|
| Backend derleme ve testler | FOG-24 | Backend değiştiğinde |
| Backend test kapsamı | FOG-23 | Backend değiştiğinde |
| Frontend tip kontrolü, testler ve derleme | FOG-24 | Frontend değiştiğinde |
| Kod stili denetimi | FOG-28 | İlgili kod değiştiğinde |
| Commit mesajı denetimi | FOG-29 | Her PR'da |
| Gizli bilgi taraması | FOG-17 | Her PR'da |
| Bağımlılık açığı taraması | FOG-18 | Her PR'da ve düzenli aralıklarla |

- Kontroller yol filtreleriyle yalnızca ilgili dosyalar değiştiğinde çalıştırılır (ADR-0001).
- Kontrollerde kullanılacak araçlar, ilgili bölüm kurulurken ayrıca belirlenecektir.
- Birleştirme commit'leri, Conventional Commits biçiminde olmadığından commit mesajı denetiminin dışında tutulur (ADR-0002).
- CI 12 Kasım 2026'da kurulmuştur (İ-09); iş tanımları `.github/workflows/` klasöründedir, kullanılan araçlar ADR-0018'in 5. bölümündedir. Yukarıdaki tablodan üç fark vardır:
  - Python işçisi için de aynı kontroller çalışır: kod stili, tür denetimi, testler ve test kapsamı (işçi veya geçiş betikleri değiştiğinde).
  - Prometheus'un uyarı kuralları `promtool` ile denetlenir ve test edilir (kural dosyaları değiştiğinde; İ-33).
  - Bağımlılık açığı taraması her PR'da değil, kod, imaj veya Kubernetes dosyaları değiştiğinde ve haftada bir çalışır. Tarama üç konteyner imajını derlediğinden, yalnızca doküman değişen PR'larda çalıştırılmaz.

### İş takibi

- İşler **GitHub Issues** ile kaydedilir ve **GitHub Projects** panosunda izlenir.
- Pano sütunları: **Todo**, **In Progress**, **Done**
- Etiketler üç gruptan oluşur:
  - **Tür:** `feat`, `fix`, `docs`, `test`, `chore`
  - **Alan:** `backend`, `frontend`, `altyapi`
  - **Öncelik:** `must`, `should`, `could`
- Issue'lar haftalık kilometre taşlarına (milestone) bağlanır. Her kilometre taşı bir Cuma değerlendirmesiyle sona erer.
- Bir gereksinimi karşılayan issue'nun açıklamasında ilgili gereksinim kimliği belirtilir (örnek: FG-AR-01).
- PR'lar ve doğrudan `main`'e yapılan doküman commit'leri, ilgili issue'yu `Closes #n` ifadesiyle kapatır.

## Sonuçlar

- Her iş GitHub'da bir issue, bir dal ve bir PR olarak izlenebilir; yapılan işin gereksinimle bağlantısı issue üzerinden kurulur.
- Merge commit kullanıldığından, dallarda yapılan düzenli çalışma `main` geçmişinde görünür kalır.
- `main` dalı, Free plandaki özel depoda dal koruma kurallarıyla doğrudan gönderime karşı korunamaz. Akış disiplinle uygulanır; CI'ın `main`'e yapılan her gönderimde de çalışması, kural dışı bir gönderimin fark edilmesini sağlar (R-34).
- PR onayı aranmadığından inceleme, PR şablonundaki kontrol listesi ve CI kontrolleriyle yapılır.
- GitHub Actions'ın özel depolardaki kullanım süresi sınırlı olduğundan, yol filtreleri ve önbellek kullanımı CI tasarımında dikkate alınacaktır.
- Haftalık kilometre taşları, haftalık ilerleme notlarının hazırlanmasında kullanılacaktır.

## Kaynaklar

- GitHub dokümantasyonu, "About rulesets": https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets