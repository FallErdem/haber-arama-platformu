// Performans testlerinin kullanıcı senaryosu (İ-38, test stratejisi 6.2 ve 6.3).
//
// Bütün testler aynı kullanıcı davranışını kullanır; yalnızca kullanıcı sayısı ve süre değişir (TEST ortam değişkeni):
//   %70 arama (filtreli ve filtresiz), %20 haber detayı, %10 kaydetme ve kaydedilenler; işlemler arasında 3-5 saniye.
// Sonuçlardaki görseller de istenir. Tarayıcı görselleri önbelleğe aldığı için (Cache-Control: private, max-age) her
// sanal kullanıcı aynı görseli bir kez ister.
//
// Hedefler eşik (threshold) olarak yazılıdır; eşik aşılırsa k6 testi başarısız sayar.

import http from 'k6/http';
import { check, sleep } from 'k6';
import exec from 'k6/execution';
import { Trend } from 'k6/metrics';

const BASE_URL = 'http://haber.localhost';
const TOKEN_URL = `${BASE_URL}/auth/realms/haber/protocol/openid-connect/token`;
const CLIENT_ID = 'haber-loadtest';
const USER_COUNT = 10;
// Erişim token'ı 5 dakika geçerlidir (realm ayarı); süresi dolmadan 4 dakikada bir yenilenir.
const TOKEN_LIFETIME_MS = 4 * 60 * 1000;
// Sonuç sayfasında tarayıcının ilk yüklediği görsel sayısı (görsel tembel yüklenir; ekranda ilk görünenler).
const IMAGES_PER_RESULT_PAGE = 8;

// Şifre setup.sh'ın oluşturduğu dosyadan okunur; komut satırına ve sonuçlara yazılmaz.
const PASSWORD = open('/secrets/loadtest-users.env')
  .split('\n')
  .find((line) => line.startsWith('password='))
  .slice('password='.length)
  .trim();

// Gerçek haberlerde sık geçen kelimeler (deneme verisi de gerçek haberlerin kelimelerinden üretildi).
const SEARCH_TERMS = [
  'ekonomi', 'enflasyon', 'seçim', 'deprem', 'futbol', 'galatasaray', 'fenerbahçe', 'erdoğan', 'iran', 'israil',
  'gazze', 'ukrayna', 'rusya', 'trump', 'merkez bankası', 'dolar', 'altın', 'hava durumu', 'öğretmen', 'sağlık',
  'yapay zeka', 'teknoloji', 'eğitim', 'cumhurbaşkanı', 'meclis', 'asgari ücret', 'emekli', 'trafik kazası', 'yangın',
  'istanbul', 'election', 'climate', 'economy', 'ukraine', 'israel', 'technology', 'health', 'artificial intelligence',
  'market', 'film',
];
const CATEGORIES = ['GENERAL', 'WORLD', 'ECONOMY', 'SPORTS', 'HEALTH', 'SCIENCE_TECH', 'CULTURE_ARTS', 'LIFESTYLE'];

// Hedefler test stratejisinin 6.3 tablosundan.
const LOAD_TARGETS = {
  search_duration: ['p(95)<500', 'p(99)<1000'],
  http_req_failed: ['rate<0.01'],
};

const PROFILES = {
  // Yük (ve 1 milyon haberle hacim): 50 eş zamanlı kullanıcı, 15 dakika.
  load: {
    scenarios: {
      users: {
        executor: 'ramping-vus',
        stages: [
          { duration: '1m', target: 50 },
          { duration: '15m', target: 50 },
          { duration: '30s', target: 0 },
        ],
      },
    },
    thresholds: LOAD_TARGETS,
  },
  // Ani yük: 50 kullanıcıdan 10 saniyede 200'e, 2 dakika, sonra 50'ye; toparlanma için 2 dakika daha.
  spike: {
    scenarios: {
      users: {
        executor: 'ramping-vus',
        stages: [
          { duration: '1m', target: 50 },
          { duration: '10s', target: 200 },
          { duration: '2m', target: 200 },
          { duration: '10s', target: 50 },
          { duration: '2m', target: 50 },
          { duration: '10s', target: 0 },
        ],
      },
    },
    thresholds: { http_req_failed: ['rate<0.05'] },
  },
  // Stres: 50 kullanıcıdan başlayıp her 2 dakikada 25 artar; hata %5'i veya arama p95'i 2 saniyeyi aşınca durur.
  stress: {
    scenarios: {
      users: {
        executor: 'ramping-vus',
        stages: [{ duration: '1m', target: 50 }].concat(
          Array.from({ length: 11 }, (_, step) => ({ duration: '2m', target: 50 + 25 * step })),
        ),
      },
    },
    thresholds: {
      http_req_failed: [{ threshold: 'rate<0.05', abortOnFail: true, delayAbortEval: '1m' }],
      search_duration: [{ threshold: 'p(95)<2000', abortOnFail: true, delayAbortEval: '1m' }],
    },
  },
  // Ölçeklenebilirlik: düşünme süresi olmadan, saniyedeki işlem sayısı her dakika 10 artar (en çok 200); yük hedefi
  // aşılınca durur. Durmadan önceki son hız, o kopya sayısında hedefleri sağlayan en yüksek hızdır.
  // Önce 3 dakika ısınma: API yeni açılmışsa Java'nın açılıştaki derlemesi (JIT) düşük CPU sınırında dakikalar sürer.
  // Eşikler yalnızca hızın artırıldığı `actions` senaryosuna bakar; ısınmanın yavaş istekleri sonuca karışmaz.
  scale: {
    scenarios: {
      warmup: {
        executor: 'constant-arrival-rate',
        rate: 10,
        timeUnit: '1s',
        duration: '3m',
        preAllocatedVUs: 20,
        maxVUs: 200,
      },
      actions: {
        executor: 'ramping-arrival-rate',
        startTime: '3m',
        startRate: 10,
        timeUnit: '1s',
        preAllocatedVUs: 50,
        maxVUs: 400,
        stages: Array.from({ length: 19 }, (_, step) => ({ duration: '1m', target: 10 + 10 * (step + 1) })),
      },
    },
    thresholds: {
      'search_duration{scenario:actions}': [{ threshold: 'p(95)<500', abortOnFail: true, delayAbortEval: '30s' }],
      'http_req_failed{scenario:actions}': [{ threshold: 'rate<0.01', abortOnFail: true, delayAbortEval: '30s' }],
    },
  },
  // Uzun süre: 50 kullanıcı, DURATION_MINUTES dakika (bellek ve bağlantı sızıntısı Prometheus'tan izlenir).
  soak: {
    scenarios: {
      users: {
        executor: 'constant-vus',
        vus: 50,
        duration: `${__ENV.DURATION_MINUTES || 120}m`,
      },
    },
    thresholds: LOAD_TARGETS,
  },
};

if (!PROFILES[__ENV.TEST]) {
  throw new Error(`Bilinmeyen test: ${__ENV.TEST} (load, spike, stress, scale, soak)`);
}

export const options = Object.assign({ summaryTrendStats: ['avg', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'] }, PROFILES[__ENV.TEST]);

// İşlem türüne göre süreler; özet raporda ayrı ayrı görünür.
const searchDuration = new Trend('search_duration', true);
const detailDuration = new Trend('detail_duration', true);
const imageDuration = new Trend('image_duration', true);
const saveDuration = new Trend('save_duration', true);

const THINK_TIME = __ENV.TEST !== 'scale';

// Her sanal kullanıcının (VU) kendi durumu: k6'da modül düzeyindeki değişkenler VU'ya özeldir.
let token = null;
let tokenFetchedAt = 0;
const knownArticleIds = [];
const loadedImages = new Set();

function username() {
  // 50 sanal kullanıcı 10 test hesabını paylaşır.
  const number = ((exec.vu.idInTest - 1) % USER_COUNT) + 1;
  return `yuktesti${String(number).padStart(2, '0')}`;
}

function fetchToken(user) {
  const response = http.post(
    TOKEN_URL,
    { grant_type: 'password', client_id: CLIENT_ID, username: user, password: PASSWORD },
    { tags: { type: 'token' } },
  );
  check(response, { 'token alındı': (r) => r.status === 200 });
  return response.status === 200 ? response.json('access_token') : null;
}

function authHeaders() {
  if (token === null || Date.now() - tokenFetchedAt > TOKEN_LIFETIME_MS) {
    token = fetchToken(username());
    tokenFetchedAt = Date.now();
  }
  return { headers: { Authorization: `Bearer ${token}` } };
}

function pick(values) {
  return values[Math.floor(Math.random() * values.length)];
}

function rememberArticles(items) {
  for (const item of items) {
    knownArticleIds.push(item.id);
  }
  knownArticleIds.splice(0, Math.max(0, knownArticleIds.length - 100));
}

function loadImages(urls) {
  const fresh = urls.filter((url) => url && !loadedImages.has(url));
  if (fresh.length === 0) {
    return;
  }
  // Tarayıcı gibi aynı anda; görsel adresi imzalıdır, token gönderilmez.
  const responses = http.batch(fresh.map((url) => ['GET', `${BASE_URL}${url}`, null, { tags: { type: 'image' } }]));
  responses.forEach((response, index) => {
    imageDuration.add(response.timings.duration);
    check(response, { 'görsel 200': (r) => r.status === 200 });
    loadedImages.add(fresh[index]);
  });
}

function search() {
  const params = [];
  // Aramaların %80'i kelimeyle, %20'si kelimesiz (en yeni haberler).
  if (Math.random() < 0.8) params.push(`q=${encodeURIComponent(pick(SEARCH_TERMS))}`);
  if (Math.random() < 0.3) params.push(`categories=${pick(CATEGORIES)}`);
  if (Math.random() < 0.2) params.push(`language=${pick(['tr', 'en'])}`);
  if (Math.random() < 0.1) {
    const to = new Date();
    const from = new Date(to.getTime() - 7 * 24 * 60 * 60 * 1000);
    params.push(`from=${from.toISOString().slice(0, 19)}Z`, `to=${to.toISOString().slice(0, 19)}Z`);
  }
  if (Math.random() < 0.2) params.push(`page=${1 + Math.floor(Math.random() * 2)}`);

  const response = http.get(`${BASE_URL}/api/v1/articles?${params.join('&')}`, Object.assign(authHeaders(), {
    tags: { type: 'search', name: 'GET /api/v1/articles' },
  }));
  searchDuration.add(response.timings.duration);
  if (!check(response, { 'arama 200': (r) => r.status === 200 })) {
    return;
  }
  const items = response.json('items') || [];
  rememberArticles(items);
  loadImages(items.slice(0, IMAGES_PER_RESULT_PAGE).map((item) => item.image && item.image.url));
}

function detail() {
  if (knownArticleIds.length === 0) {
    search();
    return;
  }
  const response = http.get(`${BASE_URL}/api/v1/articles/${pick(knownArticleIds)}`, Object.assign(authHeaders(), {
    tags: { type: 'detail', name: 'GET /api/v1/articles/{id}' },
  }));
  detailDuration.add(response.timings.duration);
  if (check(response, { 'detay 200': (r) => r.status === 200 })) {
    const media = response.json('media') || [];
    loadImages(media.slice(0, 1).map((item) => item.url));
  }
}

function savedArticles() {
  if (knownArticleIds.length === 0) {
    search();
    return;
  }
  const choice = Math.random();
  let response;
  if (choice < 0.5) {
    response = http.put(`${BASE_URL}/api/v1/me/saved-articles/${pick(knownArticleIds)}`, null, Object.assign(authHeaders(), {
      tags: { type: 'save', name: 'PUT /api/v1/me/saved-articles/{id}' },
    }));
  } else if (choice < 0.8) {
    response = http.get(`${BASE_URL}/api/v1/me/saved-articles`, Object.assign(authHeaders(), {
      tags: { type: 'save', name: 'GET /api/v1/me/saved-articles' },
    }));
  } else {
    response = http.del(`${BASE_URL}/api/v1/me/saved-articles/${pick(knownArticleIds)}`, null, Object.assign(authHeaders(), {
      tags: { type: 'save', name: 'DELETE /api/v1/me/saved-articles/{id}' },
    }));
  }
  saveDuration.add(response.timings.duration);
  check(response, { 'kaydetme 2xx': (r) => r.status >= 200 && r.status < 300 });
}

// Test başlamadan bir kez: her test kullanıcısı giriş yapabiliyor ve uygulamada onaylı (ACTIVE) mı?
// Değilse test başlamaz; aksi halde istekler 403 alır ve ölçülen şey sistem değil yetki hatası olurdu.
export function setup() {
  for (let number = 1; number <= USER_COUNT; number++) {
    const user = `yuktesti${String(number).padStart(2, '0')}`;
    const accessToken = fetchToken(user);
    const me = accessToken
      ? http.get(`${BASE_URL}/api/v1/me`, { headers: { Authorization: `Bearer ${accessToken}` }, tags: { type: 'setup' } })
      : null;
    const status = me && me.status === 200 ? me.json('status') : null;
    if (status !== 'ACTIVE') {
      exec.test.abort(`${user} kullanılamıyor (durum: ${status}); setup.sh çalıştırılıp kullanıcılar onaylanmalı`);
    }
  }
}

export default function () {
  const choice = Math.random();
  if (choice < 0.7) {
    search();
  } else if (choice < 0.9) {
    detail();
  } else {
    savedArticles();
  }
  if (THINK_TIME) {
    sleep(3 + Math.random() * 2);
  }
}
