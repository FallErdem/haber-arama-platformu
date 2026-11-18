#!/usr/bin/env bash
# ADR-0019'un 2. adımını kümeye uygular: haber metinleri (özet, tam metin, yazar) PostgreSQL'den
# kaldırılır, yalnızca Elasticsearch'te kalır. Tek seferlik bir betiktir; commit'lenmiş kodla çalışır.
#
# Neden ayrı bir betik: V14 sütunları siler ve API açılırken çalışır. Eski işçi V14'ten sonra çalışırsa
# silinen sütunlara yazmaya, yeni işçi V14'ten önce çalışırsa henüz olmayan outbox_events.payload
# sütununa yazmaya çalışır. deploy-*.sh betikleri bütün overlay'i uyguladığı için durdurulmuş işçiyi
# de yeniden açar (Deployment'ta replicas: 1); bu betik imajları sırayla, tek tek değiştirir.
#
# Adımlar:
#   1. API ve işçi imajları derlenip gönderilir (kümeye henüz dokunulmaz).
#   2. İşçi durdurulur.
#   3. Silmeden önce denetlenir: görünür her haberin ya arama indeksinde belgesi ya da bekleyen bir
#      outbox notu olmalıdır (V14, bekleyen notlara ve gizli haberlere metni kendisi taşır).
#   4. Onay istenir: sütunların silinmesi geri alınamaz.
#      1-4 arasında bir sorun çıkarsa işçi eski haliyle yeniden açılır; hiçbir şey değişmemiştir.
#   5. Yalnızca API'nin imajı değiştirilir; API açılırken Flyway V14'ü tek işlemde uygular. Eski API
#      kopyası kapanana kadar (yaklaşık bir dakika) arama ve detay hata verebilir.
#   6. Durdurulmuş işçinin ve yeniden indeksleme işinin imajı değiştirilir.
#   7. Yeniden indeksleme: yeni nesil, belgelere eklenen hidden alanıyla açılır (şablon yalnızca yeni
#      indekslere uygulanır). reindex.sh bitince işçiyi açar; işçi artık yeni imajdadır.
#   8. Overlay uygulanır (imaj etiketleri zaten aynıdır; küme dosyalarla eşitlenir) ve sonuç gösterilir.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OVERLAY="$REPO_ROOT/deploy/k8s/overlays/dev"
NAMESPACE="haber"
# Docker yalnızca 127.0.0.1 adresine şifresiz (HTTP) gönderir; küme aynı imajı ikinci adla çeker.
PUSH_REGISTRY="127.0.0.1:5000"
CLUSTER_REGISTRY="haber-registry.localhost:5000"

cd "$REPO_ROOT"

# Kümedeki veritabanında tek bir sorgu çalıştırır ve yalnızca sonucu yazar (süper kullanıcıyla, pod içinde).
query() {
  kubectl exec -n "$NAMESPACE" postgres-1 -c postgres -- psql -U postgres -d news -X -q -t -A -c "$1"
}

# Arama indeksindeki belge sayısı. Önce yenilenir: son yazılan belgeler de sayılsın. curl -f, hata
# yanıtında (401, 503) komutu başarısız yapar; yanıt yalnızca {"count":N} biçimindeyse sayı kabul edilir.
document_count() {
  local es_pw response
  es_pw=$(grep '^password=' deploy/k8s/overlays/dev/secrets/elasticsearch-news-worker.env | cut -d= -f2)
  kubectl exec -n "$NAMESPACE" elasticsearch-0 -- \
    curl -sf -o /dev/null -u "news_worker:$es_pw" -X POST 'localhost:9200/articles/_refresh'
  response=$(kubectl exec -n "$NAMESPACE" elasticsearch-0 -- \
    curl -sf -u "news_worker:$es_pw" 'localhost:9200/articles/_count?filter_path=count')
  if [[ ! "$response" =~ ^\{\"count\":([0-9]+)\}$ ]]; then
    echo "Belge sayısı okunamadı: $response" >&2
    return 1
  fi
  echo "${BASH_REMATCH[1]}"
}

v14_applied() {
  [[ "$(query "SELECT count(*) FROM flyway_schema_history WHERE version = '14' AND success")" == "1" ]]
}

if [[ -n "$(git status --porcelain -- backend worker db/migrations)" ]]; then
  echo "backend/, worker/ veya db/migrations/ altında commit'lenmemiş değişiklik var; kümeye commit'lenmiş kod gider." >&2
  exit 1
fi
if v14_applied; then
  echo "V14 zaten uygulanmış. Yarıda kaldıysa kalan adım yeniden indekslemedir: ./scripts/dev/reindex.sh" >&2
  exit 1
fi
TAG="$(git rev-parse --short HEAD)"

echo "1/8 İmajlar derleniyor: $TAG"
docker build -f backend/Dockerfile -t "$PUSH_REGISTRY/newssearch-api:$TAG" .
docker push "$PUSH_REGISTRY/newssearch-api:$TAG"
docker build -f worker/Dockerfile -t "$PUSH_REGISTRY/newssearch-worker:$TAG" .
docker push "$PUSH_REGISTRY/newssearch-worker:$TAG"

echo "2/8 İşçi durduruluyor"
# Onaya kadar betik nasıl biterse bitsin (denetim tutmadı, bir komut hata verdi, Ctrl+C) işçi eski
# haliyle yeniden açılır: veritabanı henüz değişmemiştir.
trap 'echo "Hiçbir şey değişmedi; işçi eski haliyle yeniden başlatılıyor."; kubectl scale -n "$NAMESPACE" deployment/worker --replicas=1' EXIT
kubectl scale -n "$NAMESPACE" deployment/worker --replicas=0
kubectl wait -n "$NAMESPACE" --for=delete pod -l app=worker --timeout=120s

echo "3/8 Denetleniyor"
visible=$(query "SELECT count(*) FROM articles WHERE NOT hidden")
pending=$(query "SELECT count(DISTINCT e.article_id) FROM outbox_events e JOIN articles a ON a.id = e.article_id
                 WHERE e.status = 'PENDING' AND NOT a.hidden")
hidden=$(query "SELECT count(*) FROM articles WHERE hidden")
documents=$(document_count)
echo "Görünür haber: $visible, indeksteki belge: $documents, bekleyen notu olan görünür haber: $pending, gizli haber: $hidden"
# Belgesi olmayan her görünür haberin metni, bekleyen bir notla taşınabilmelidir.
if ((visible - documents > pending)); then
  echo "Belgesi de bekleyen notu da olmayan $((visible - documents - pending)) haber var; metinleri kaybolurdu." >&2
  echo "Önce yeniden indeksleme yapılmalı: ./scripts/dev/reindex.sh" >&2
  exit 1
fi

echo
echo "4/8 V14, haber tablosundaki özet, tam metin ve yazar sütunlarını kalıcı olarak silecek."
read -r -p "Devam etmek için 'evet' yazın: " answer
if [[ "$answer" != "evet" ]]; then
  exit 1
fi

# Bundan sonra bir adım başarısız olursa işçi durdurulmuş kalır: V14'ten sonra eski imajla açılması
# güvenli değildir.
trap 'status=$?; if ((status != 0)); then echo "Betik yarıda kaldı; işçi durdurulmuş bırakıldı. Kalan adımları elle tamamlayın." >&2; fi' EXIT

# Overlay'deki etiketler (deploy-*.sh betikleriyle aynı yöntem; etiket tırnak içinde, bkz. deploy-api.sh).
for image in newssearch-api newssearch-worker; do
  sed -i "/name: .*\/$image\$/{n;s|newTag: .*|newTag: \"$TAG\"|;}" "$OVERLAY/kustomization.yaml"
done

echo "5/8 API güncelleniyor; Flyway V14'ü uygulayacak"
kubectl set image -n "$NAMESPACE" deployment/api "api=$CLUSTER_REGISTRY/newssearch-api:$TAG"
kubectl rollout status -n "$NAMESPACE" deployment/api --timeout=300s
if ! v14_applied; then
  echo "V14 uygulanmamış görünüyor; API loglarına bakın: kubectl logs -n $NAMESPACE deploy/api" >&2
  exit 1
fi

echo "6/8 İşçinin ve yeniden indeksleme işinin imajı değiştiriliyor (işçi durdurulmuş kalır)"
kubectl set image -n "$NAMESPACE" deployment/worker "worker=$CLUSTER_REGISTRY/newssearch-worker:$TAG"
kubectl set image -n "$NAMESPACE" cronjob/worker-reindex "reindex=$CLUSTER_REGISTRY/newssearch-worker:$TAG"

echo "7/8 Yeniden indeksleme"
./scripts/dev/reindex.sh

echo "8/8 Küme dosyalarla eşitleniyor"
kubectl apply -k "$OVERLAY"
kubectl rollout status -n "$NAMESPACE" deployment/worker --timeout=120s

echo
echo "Sonuç (bekleyen notlar işlenince ilk iki sayı eşitlenir; birkaç saniye sonra tekrar bakılabilir):"
echo "Haber (gizliler dahil): $(query "SELECT count(*) FROM articles")"
echo "İndeksteki belge (gizliler dahil): $(document_count)"
echo "Metin taşıyan bekleyen not: $(query "SELECT count(*) FROM outbox_events WHERE status = 'PENDING' AND payload IS NOT NULL")"
echo "Metni boşaltılmamış işlenmiş not (0 olmalı): $(query "SELECT count(*) FROM outbox_events WHERE status = 'PROCESSED' AND payload IS NOT NULL")"
