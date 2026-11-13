# ADR-0002: Commit Mesajı Standardı Olarak Conventional Commits

- **Durum:** Kabul edildi
- **Tarih:** 2026-11-02

## Bağlam

Şartname, sektörde kullanılan bir commit standardının araştırılıp uygulanmasını ve commit'lerin düzenli ve anlamlı olmasını istemektedir. Proje ilerlemesi commit geçmişi üzerinden değerlendirilmektedir. Depo monorepo yapısındadır (ADR-0001), bu nedenle bir commit'in projenin hangi parçasını etkilediğinin mesajdan anlaşılabilmesi faydalıdır. Depodaki dokümanların ve commit mesajlarının dili Türkçe olarak belirlenmiştir.

## Değerlendirilen Seçenekler

### 1. Serbest format

- Artı: Öğrenme maliyeti yoktur.
- Eksi: Mesajlar zamanla tutarsızlaşır, geçmiş okunamaz hale gelir.
- Eksi: Otomatik denetlenemez; şartnamenin standart seçilmesi beklentisini karşılamaz.

### 2. Conventional Commits

- Artı: Sektörde yaygın kullanılan, açık bir şartnamesi olan standarttır.
- Artı: `tür(kapsam): açıklama` yapısı commit'in türünü ve etkilediği parçayı ilk bakışta gösterir.
- Artı: Makine tarafından okunabilir; CI'da otomatik denetlenebilir, değişiklik listesi ve anlamsal sürüm (SemVer) üretiminde kullanılabilir.
- Artı: `Closes #12` gibi alt bilgilerle commit'ler GitHub issue'larına bağlanabilir.
- Eksi: Tür kelimeleri İngilizcedir; Türkçe çevirileri standart araçlar tarafından tanınmaz.

### 3. Gitmoji

- Artı: Geçmiş görsel olarak hızlı taranabilir.
- Eksi: Emojilerin anlamlarının ezberlenmesi gerekir.
- Eksi: Bazı terminal ve araçlarda düzgün görüntülenmeyebilir; Conventional Commits kadar araç desteği yoktur.

## Karar

Conventional Commits kullanılacaktır. Projeye uygulanma biçimi:

- Tür kelimeleri İngilizce kalır (`feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `build`, `ci`, `chore`, `style`, `revert`); böylece standart araçlarla uyumluluk korunur.
- Açıklama, gövde ve alt bilgi Türkçe yazılır.
- Açıklama geçmiş zaman edilgen kipte yazılır (örnek: `docs: kapsam dokümanı eklendi`).
- Başlık satırı kısa tutulur; gövdede değişikliğin ne olduğundan çok neden yapıldığı açıklanır.
- Her commit tek bir mantıksal değişiklik içerir.
- İlgili issue'lar alt bilgide belirtilir (`Closes #12`).
- Kapsam listesi depo klasör yapısı belirlendikten sonra tanımlanacaktır.

## Sonuçlar

- Commit geçmişi tür ve kapsama göre okunabilir ve filtrelenebilir olur.
- Kurallar ileride commitlint gibi bir araçla otomatik denetlenecek, uymayan commit'ler engellenecektir.
- Denetim 12 Kasım 2026'da kurulmuştur (İ-09): `scripts/ci/check-commit-messages.sh` betiği, PR'daki commit başlıklarının `<tür>: <açıklama>` biçimine ve yukarıdaki tür listesine uyduğunu denetler; birleştirme commit'leri denetlenmez. commitlint yerine kısa bir betik tercih edilmiştir: commitlint bir Node aracıdır ve tek bir biçim kontrolü için deponun köküne ayrı bir paket listesi ve yüzlerce dolaylı bağımlılık getirirdi. Betik yalnızca biçimi denetler; açıklamanın dili ve kipi gözle kontrol edilir.