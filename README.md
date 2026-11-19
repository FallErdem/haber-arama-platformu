# Haber Arama Platformu

Farklı haber kaynaklarından haberleri toplayan, tek yerde birleştirerek aranabilir hale getiren ve sonuçları görselleriyle birlikte, özgün habere bağlantı vererek gösteren bir web uygulaması.

## Durum (19 Kasım 2026)

Çalışan işlevler:

- **Haber toplama:** TRT Haber, NTV, CNN Türk ve Global Voices'ın 42 RSS/Atom beslemesinden düzenli toplama; kategori eşlemesi, tekrar kontrolü, hata durumunda yeniden deneme ve beslemenin kendiliğinden devre dışı kalması; görsellerin indirilmesi.
- **Arama:** Türkçe ve İngilizce tam metin arama (Türkçe karaktersiz yazımla da), kaynak, dil, kategori ve tarih filtreleri, Son Dakika, ilgililiğe veya tarihe göre sıralama, eşleşen kelimelerin vurgulanması, sayfalama.
- **Haber detayı:** Temizlenmiş tam metin, görseller, kaynak ve atıf bilgisi, özgün habere bağlantı.
- **Kaydedilen haberler:** Arama sonuçlarından ve detaydan yer imiyle kaydetme, Kaydedilenler sayfası.
- **Kimlik ve yetki:** Keycloak ile kayıt ve giriş, yönetici onayı, kullanıcı durumları (onay bekliyor, aktif, pasif, reddedildi).
- **Yönetim paneli:** Kullanıcıların listelenmesi, onaylanması, reddedilmesi, rol ve durum değişikliği, son aktif yönetici kuralı.
- **Audit log:** Kullanıcı kaydı, yeni oturum, reddedilen istekler ve kullanıcı yönetimi işlemleri; kayıtlar değiştirilemez ve silinemez.

Sıradaki işler: yönetim panelinde kaynaklar, toplama geçmişi, audit arama ve pano; NYT kaynağı; yaşam döngüsü işleri; üretim ayarları (HTTPS, gözlemlenebilirlik, yedekleme) ve uçtan uca testler. Plan: `docs/09-is-plani.md`.

## Mimari

```
Tarayıcı ──► Traefik (Gateway API) ──┬──► Frontend (React, nginx)        haber.localhost/
                                     ├──► API (Spring Boot)               haber.localhost/api/
                                     └──► Keycloak                        haber.localhost/auth/

API ──► PostgreSQL (asıl kayıt) · Elasticsearch (arama, okuma) · MinIO (görseller, okuma)
İşçi (Python) ──► haber kaynakları · PostgreSQL · Elasticsearch (yazma) · MinIO (yazma)
```

- **API** (Java 25, Spring Boot 4.1): Kullanıcı ve yönetici isteklerini karşılar. Modüler monolit; modüller `identity`, `ingestion`, `search`, `library`, `admin`, `audit`, sınırları Spring Modulith ile denetlenir.
- **İşçi** (Python 3.14, asyncio): Bütün arka plan işleri: haber toplama, görsel indirme, arama indeksine aktarım (outbox).
- **İki uygulama doğrudan konuşmaz**, yalnızca veri depoları üzerinden haberleşir.
- **Frontend** (React, TypeScript, Vite, shadcn/ui, TanStack Query).
- **Veri:** PostgreSQL meta veriyi ve kullanıcıları, Elasticsearch haber metinlerini ve arama indeksini, MinIO görselleri tutar.
- Hepsi yerel bir Kubernetes kümesinde (k3d) çalışır.

Ayrıntılar: `docs/04-mimari.md` ve `docs/adr/`.

## Kurulum

Boş bir Ubuntu bilgisayarda sıfırdan kurulum (araçların kurulumu dahil): **[`deploy/README.md`](deploy/README.md)**.

Kısaca: Docker, kubectl, Helm ve k3d kurulur; küme oluşturulur, altyapı bileşenleri kurulur, üç uygulama betiklerle derlenip dağıtılır ve uygulama `http://haber.localhost/` adresinden açılır. Bilgisayarda Java, Node.js veya Python gerekmez; imajlar Docker'ın içinde derlenir.

## Depo düzeni

| Klasör | İçerik |
|---|---|
| `backend/` | Spring Boot API |
| `worker/` | Python işçisi (`news_worker`) |
| `frontend/` | React uygulaması |
| `db/migrations/` | Veritabanı geçiş betikleri (Flyway, `V1` – `V15`) |
| `deploy/` | k3d kümesi ve Kubernetes dosyaları (Kustomize) |
| `scripts/dev/` | Derleme, dağıtım ve bakım betikleri |
| `docs/` | Gereksinimler, mimari, veri modeli, API sözleşmesi, ekran akışları, kararlar (ADR) |

## Testler

Testleri bilgisayarda çalıştırmak için ilgili araçlar ve Docker gerekir (entegrasyon testleri gerçek PostgreSQL, Elasticsearch ve MinIO'yu Testcontainers ile Docker'da başlatır). CI aynı komutları her gönderimde çalıştırır (`.github/workflows/`).

| Uygulama | Gerekenler | Komut |
|---|---|---|
| API | JDK 25, Docker | `cd backend && ./mvnw verify` |
| İşçi | uv 0.13.6 (Python 3.14'ü kendisi kurar), Docker | `cd worker && uv sync --locked && uv run pytest` |
| Frontend | Node.js 26.12.1 | `cd frontend && npm ci && npm test` |

Kod stili ve tür denetimleri: API'de `verify` içinde (Spotless); işçide `uv run ruff check .` ve `uv run mypy`; frontend'de `npm run lint` ve `npm run format:check`.

## Dokümanlar

| Dosya | İçerik |
|---|---|
| `docs/01-kapsam.md` | Kimin için, hangi sorun, kapsam dışı |
| `docs/02-gereksinimler.md` | Fonksiyonel ve fonksiyonel olmayan gereksinimler |
| `docs/03-riskler.md` | Risk kaydı |
| `docs/04-mimari.md` | Bileşenler, modüller, akışlar |
| `docs/05-veri-modeli.md` | PostgreSQL tabloları, Elasticsearch, MinIO, veritabanı kullanıcıları |
| `docs/06-api-sozlesmesi.md` | `/api/v1/` uç noktaları ve hata kodları |
| `docs/07-ekran-akislari.md` | Ekranlar ve uçtan uca senaryolar |
| `docs/08-test-stratejisi.md` | Test türleri ve hedefleri |
| `docs/09-is-plani.md` | İş kalemleri ve haftalara dağılım |
| `docs/10-kodlama-standartlari.md` | Kodlama kuralları |
| `docs/adr/` | Mimari kararlar ve gerekçeleri |
| `docs/ilerleme/` | Haftalık ilerleme notları |
