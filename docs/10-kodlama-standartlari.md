# Kodlama Standartları

## 1. Amaç

Bu doküman, Spring Boot API, Python işçisi ve React frontend için geçerli kodlama kurallarını tanımlar. Kod stili elle değil araçlarla denetlenir ve CI'da zorunlu tutulur (FOG-28).

## 2. Genel İlkeler

- **Tek sorumluluk:** Her sınıf ve fonksiyon tek bir iş yapar. Bir fonksiyonu adıyla anlatırken "ve" kelimesi gerekiyorsa bölünür.
- **Bağımlılıkların dışarıdan verilmesi:** Sınıflar ihtiyaç duydukları nesneleri kendileri oluşturmaz, yapıcı (constructor) üzerinden alır. Bu sayede testlerde gerçek bağımlılıkların yerine test nesneleri verilebilir.
- **Arayüze göre programlama:** Değişebilecek davranışlar bir arayüzün arkasında durur. Örnek: RSS, Atom ve NYT okuyucuları ortak bir okuyucu arayüzünü uygular; yeni bir kaynak türü eklemek yalnızca yeni bir sınıf eklemektir (Strateji deseni).
- **Kalıtım yerine bileşim:** Davranış paylaşımı, sınıf hiyerarşileri yerine nesnelerin birleştirilmesiyle sağlanır.
- **Değiştirilemez veri:** Veri taşıyan nesneler oluşturulduktan sonra değiştirilmez (Java'da `record`, Python'da `@dataclass(frozen=True)`).
- **Sihirli değer yok:** Koddaki anlamı açık olmayan sayılar ve metinler adlandırılmış sabitlere veya yapılandırmaya taşınır.
- **Ölü kod yok:** Kullanılmayan kod ve yorum satırına alınmış kod depoya girmez; geçmiş Git'te durur.
- **Gerekmeyen genellik yok:** Bugün ihtiyaç duyulmayan bir esneklik için kod yazılmaz.

## 3. Depo Düzeni

| Klasör | İçerik |
|---|---|
| `backend/` | Spring Boot API |
| `worker/` | Python işçisi |
| `frontend/` | React uygulaması |
| `db/migrations/` | Flyway geçiş betikleri (ADR-0018) |
| `docs/` | Dokümanlar ve ADR'ler |
| `scripts/` | Yardımcı betikler |

Kubernetes yapılandırma dosyalarının klasörü, yerel Kubernetes ortamı kurulurken belirlenecektir.

## 4. Adlandırma

| | Java | Python | TypeScript |
|---|---|---|---|
| Paket veya modül | `com.erdemgural.newssearch.<modül>` | `news_worker.<paket>` | Özelliğe göre klasör (`features/search/`) |
| Sınıf, bileşen | `PascalCase` (`ArticleService`) | `PascalCase` (`RssReader`) | `PascalCase` (`SearchPage`) |
| Fonksiyon, metot, değişken | `camelCase` | `snake_case` | `camelCase` |
| Sabit | `UPPER_SNAKE_CASE` | `UPPER_SNAKE_CASE` | `UPPER_SNAKE_CASE` |
| Dosya | Sınıfla aynı ad | `snake_case.py` | Bileşenler `PascalCase.tsx`, diğerleri `camelCase.ts` |

- Adlar ne olduğunu söyler; kısaltma kullanılmaz (`articleRepository`, `ar` değil).
- Boolean adları bir soru gibi okunur (`isHidden`, `hasImage`).
- Adlar İngilizce yazılır (ADR-0015).

## 5. Yorumlar

- Yorumlar **Türkçe** yazılır.
- Yorumlar kodun **ne** yaptığını değil, **neden** öyle yaptığını açıklar. Kodun ne yaptığı adlardan anlaşılmalıdır.
- Modüllerin dışa açtığı sınıflar ve fonksiyonlar Javadoc veya docstring ile belgelenir.
- Bir kararın gerekçesi bir ADR'deyse yorumda ADR'ye atıf yapılır.

## 6. Spring Boot API

- **Paket yapısı:** Her modül `com.erdemgural.newssearch` altında bir pakettir. Modülün başka modüllere açtığı sınıflar modülün kök paketinde; iç sınıflar alt paketlerde durur. Spring Modulith bu sınırı denetler (ADR-0018).
- **Katmanlar:** Controller yalnızca HTTP ile ilgilenir: isteği alır, doğrular, service'i çağırır, yanıtı döndürür. Service iş kurallarını ve işlem (transaction) sınırlarını taşır. Repository yalnızca veri erişimi yapar.
- **Yanıt nesneleri:** API'ler veritabanı nesnelerini doğrudan döndürmez; istek ve yanıtlar için ayrı `record` sınıfları kullanılır. Böylece veritabanındaki bir değişiklik API sözleşmesini kendiliğinden değiştirmez.
- **Girdi doğrulama:** İstek nesneleri Bean Validation ile, sistemin sınırında doğrulanır.
- **Bağımlılıklar:** Yalnızca yapıcı üzerinden verilir; alan üzerine `@Autowired` kullanılmaz.
- **Zaman:** Zaman değerleri UTC'dir (`Instant`). Şimdiki zaman bir `Clock` nesnesinden alınır; testlerde sabit bir saat verilebilir.
- **Harf dönüşümleri:** Dile bağlı olmaması gereken dönüşümlerde `Locale.ROOT` kullanılır.
- **Hatalar:** İş kuralı hataları kendi istisna sınıflarıyla fırlatılır ve tek bir genel hata işleyicide RFC 9457 yanıtına ve hata koduna çevrilir. İstisnalar yutulmaz.
- **Loglama:** SLF4J ile, parametreli mesajlarla (`log.info("Haber gizlendi: {}", id)`). Token, parola, API anahtarı ve istek gövdeleri loglanmaz. Loglar her ortamda Spring Boot'un yapılandırılmış log desteğiyle JSON olarak (`ecs` biçimi) yazılır; her satırda isteğin kimliği (`requestId`) bulunur ve aynı değer yanıtın `X-Request-Id` başlığındadır (FOG-39).

## 7. Python İşçisi

- **Tür bilgisi zorunlu:** Bütün fonksiyonlar tür ipuçlarıyla yazılır; mypy katı modda (`--strict`) çalışır.
- **Katmanlar:** Okuyucular (her kaynak türü için bir sınıf), servisler (toplama akışı, outbox aktarımı, görsel indirme) ve repository'ler (her tablonun SQL sorguları) ayrıdır. Servisler SQL görmez.
- **SQL:** Değerler her zaman parametre olarak gönderilir; SQL metnine hiçbir değer doğrudan eklenmez.
- **Eş zamanlılık:** Kod `asyncio` ile yazılır. Olay döngüsünü bekleten eş zamanlı çağrılar (örneğin boto3) ayrı bir iş parçacığında çalıştırılır (`asyncio.to_thread`).
- **Türkçe metin:** Türkçe küçük harf dönüşümü için ortak yardımcı fonksiyon kullanılır; `str.lower()` doğrudan kullanılmaz.
- **Loglama:** Yapılandırılmış loglar; API anahtarı içeren adresler loglanmadan önce maskelenir.

## 8. React Frontend

- **TypeScript katı modda;** `any` kullanılmaz.
- **Bileşenler:** Fonksiyon bileşenleri ve kancalar (hooks). Bileşenler küçük tutulur; ekranlar özelliklere göre klasörlenir.
- **Sunucu verisi** TanStack Query ile alınır; API yanıtlarının türleri tek bir yerde tanımlanır.
- **Metinler** dil dosyalarındadır; bileşenlerin içine metin yazılmaz (FOG-31).
- **Erişilebilirlik:** Anlamsal HTML öğeleri kullanılır; her form alanının etiketi, her görselin alternatif metni vardır (FOG-30).
- **HTML içerik:** API'den gelen HTML (haber metni, vurgular) yalnızca temizlenmiş haliyle ve izin verilen etiketlerle gösterilir.

## 9. Testler

- **Düzen:** Hazırla, çalıştır, doğrula (Arrange–Act–Assert).
- **Kapsam:** Her test tek bir davranışı test eder.
- **Adlandırma:** Test adı neyi test ettiğini ve beklenen sonucu söyler (örnek: `aynı haber ikinci kez gelince kaydedilmez`).
- **Bağımsızlık:** Testler birbirine ve çalışma sırasına bağlı değildir; her test kendi verisini hazırlar.
- Test stratejisinin geri kalanı `08-test-stratejisi.md`'dedir.

## 10. Güvenlik Kuralları

- Gizli bilgiler koda ve depoya yazılmaz; yapılandırmadan okunur (R-16).
- Girdiler sistemin sınırında doğrulanır.
- SQL sorgularına değerler yalnızca parametre olarak verilir.
- Dışarıdan gelen HTML yalnızca temizlendikten sonra saklanır ve gösterilir (FOG-16).
- Loglarda ve audit kayıtlarında gizli bilgi bulunmaz (R-18).

## 11. Araçlar

| | Biçim | Hata ve kural denetimi | Diğer |
|---|---|---|---|
| Java | Spotless ile palantir-java-format | Derleyici uyarıları; Spring Modulith (modül sınırları) | Kapsam: JaCoCo |
| Python | ruff | ruff, mypy (`--strict`) | Kapsam: pytest-cov |
| TypeScript | Prettier | ESLint (TypeScript, React kancaları ve erişilebilirlik kuralları), TypeScript derleyicisi | — |
| Bütün depo | — | gitleaks, commit öncesinde | — |

Bütün kontroller CI'da çalışır; herhangi biri başarısız olursa PR birleştirilmez (ADR-0008).

Kod yazdıktan sonra, commit'ten önce çalıştırılacak komutlar:

| | Biçimlendir | Denetle (CI'ın çalıştırdığı) |
|---|---|---|
| Java (`backend/`) | `./mvnw spotless:apply` | `./mvnw verify` (biçim, testler ve kapsam) |
| Python (`worker/`) | `uv run ruff format .` | `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy`, `uv run pytest` |
| TypeScript (`frontend/`) | `npm run format` | `npm run format:check`, `npm run lint`, `npm test`, `npm run build` |
| Commit başlıkları | — | `scripts/ci/check-commit-messages.sh origin/main HEAD` |

**Seçimlerin gerekçeleri:**

- **palantir-java-format:** Yapılandırma gerektirmez ve her zaman aynı sonucu üretir; 120 karakterlik satır uzunluğu, Spring kodundaki uzun zincirleme çağrıları okunaklı tutar. Alternatif google-java-format, 2 boşluk girinti ve 100 karakterlik satırla daha sık satır bölünmesine yol açar.
- **ESLint ve Prettier:** ESLint hataları, Prettier biçimi denetler; React kancalarının kurallarını ve erişilebilirlik kurallarını denetleyen eklentiler ESLint için mevcuttur. Alternatif Biome iki işi tek araçta ve daha hızlı yapar, ancak React'e özgü kural kapsamı daha dardır.
- **Türkçe yorumlar:** Dokümanlar, commit mesajları ve değerlendirme Türkçedir; yorumların da Türkçe olması kodun gerekçesinin aynı dilde anlatılmasını sağlar.