import { parseDate } from '@internationalized/date'
import { z } from 'zod'

/**
 * Arama ekranının durumu adres çubuğunda tutulur (ekran akışları 5.1): adres paylaşıldığında aynı
 * arama açılır; geri düğmesi ve sayfa yenileme aramayı korur. Örnek:
 *
 *   /?q=deprem&sources=TRT,NTV&language=tr&categories=GENERAL&from=2026-11-01&to=2026-11-18&sort=newest&page=2
 *
 * Adres kullanıcının elle değiştirebileceği bir girdidir. Bozuk bir değer API'ye gönderilmez,
 * varsayılan değere döner; böylece adresteki bir yazım hatası hata ekranı değil, çalışan bir arama
 * gösterir. Kuralları Zod tanımlar.
 */

/** Tarihler Türkiye saatiyle gösterilir ve seçilir (ekran akışları 2. bölüm). */
export const TIME_ZONE = 'Europe/Istanbul'

export const PAGE_SIZE = 20

/** API ilk 10.000 sonucun ötesine sayfalamaz (API sözleşmesi 2.4): 20'şerli sayfalarla en fazla 500 sayfa. */
export const MAX_PAGE = 10_000 / PAGE_SIZE

/** API'nin sınırıyla aynı (API sözleşmesi 4.1). */
export const MAX_QUERY_LENGTH = 200

export type SearchSort = 'relevance' | 'newest'
export type SearchLanguage = 'tr' | 'en'

export interface SearchState {
  /** Arama ifadesi; boşsa haberler tarihe göre listelenir. */
  q: string
  /** Kaynak kodları (`TRT`, `NTV`). */
  sources: string[]
  language: SearchLanguage | undefined
  /** Kategori kodları (`GENERAL`, `BREAKING`). */
  categories: string[]
  /** Yayın tarihi aralığı, Türkiye saatiyle gün olarak (`2026-11-05`); iki uç da dahil. */
  from: string | undefined
  to: string | undefined
  /** Seçilmediyse API'nin varsayılanı geçerlidir: arama ifadesi varsa ilgililik, yoksa en yeni. */
  sort: SearchSort | undefined
  /** Adreste 1'den başlar ("2. sayfa" = `page=2`); API'de 0'dan başlar (bkz. `toApiParams`). */
  page: number
}

export const EMPTY_SEARCH: SearchState = {
  q: '',
  sources: [],
  language: undefined,
  categories: [],
  from: undefined,
  to: undefined,
  sort: undefined,
  page: 1,
}

/** Kaynak ve kategori kodları büyük harf, rakam ve alt çizgiden oluşur (`SCIENCE_TECH`). */
const CODE = /^[A-Z0-9_]{1,40}$/

/** `TRT,NTV` → `['TRT', 'NTV']`. Kod biçimine uymayanlar ve tekrarlar atılır. */
const codeList = z
  .string()
  .transform((value) => [...new Set(value.split(',').map((code) => code.trim()))].filter((code) => CODE.test(code)))
  .catch([])

/** Takvimde var olan bir gün (`2026-11-05`); `2026-02-30` veya `05-11-2026` reddedilir. */
const isoDate = z
  .string()
  .refine((value) => {
    try {
      return parseDate(value).toString() === value
    } catch {
      return false
    }
  })
  .optional()
  .catch(undefined)

const searchParamsSchema = z.object({
  // Sınırdan uzun ifade atılmaz, kısaltılır: kullanıcının aradığı şeye en yakın sonuç gösterilir.
  q: z
    .string()
    .transform((value) => value.trim().slice(0, MAX_QUERY_LENGTH))
    .catch(''),
  sources: codeList,
  language: z.enum(['tr', 'en']).optional().catch(undefined),
  categories: codeList,
  from: isoDate,
  to: isoDate,
  sort: z.enum(['relevance', 'newest']).optional().catch(undefined),
  page: z.coerce.number().int().min(1).max(MAX_PAGE).catch(1),
})

/** Adres çubuğundaki parametreleri okur. Geçersiz her değer varsayılanına döner; hata fırlatmaz. */
export function parseSearchState(params: URLSearchParams): SearchState {
  const parsed = searchParamsSchema.parse({
    q: params.get('q') ?? '',
    sources: params.get('sources') ?? '',
    language: params.get('language') ?? undefined,
    categories: params.get('categories') ?? '',
    from: params.get('from') ?? undefined,
    to: params.get('to') ?? undefined,
    sort: params.get('sort') ?? undefined,
    page: params.get('page') ?? 1,
  })
  // Başlangıcı bitişinden sonra olan aralık anlamsızdır; API de reddeder. Aralık yok sayılır.
  const isRangeValid = parsed.from === undefined || parsed.to === undefined || parsed.from <= parsed.to
  return {
    q: parsed.q,
    sources: parsed.sources,
    language: parsed.language,
    categories: parsed.categories,
    from: isRangeValid ? parsed.from : undefined,
    to: isRangeValid ? parsed.to : undefined,
    sort: parsed.sort,
    page: parsed.page,
  }
}

/**
 * Durumu adres çubuğu parametrelerine çevirir. Varsayılan değerler yazılmaz; aynı arama her zaman
 * aynı adresi üretir (`/?q=deprem`, `/?q=deprem&page=1` değil).
 */
export function toUrlParams(state: SearchState): URLSearchParams {
  const params = new URLSearchParams()
  if (state.q) params.set('q', state.q)
  if (state.sources.length) params.set('sources', state.sources.join(','))
  if (state.language) params.set('language', state.language)
  if (state.categories.length) params.set('categories', state.categories.join(','))
  if (state.from) params.set('from', state.from)
  if (state.to) params.set('to', state.to)
  if (state.sort) params.set('sort', state.sort)
  if (state.page > 1) params.set('page', String(state.page))
  return params
}

/**
 * Durumu `GET /api/v1/articles` parametrelerine çevirir (API sözleşmesi 4.1). Adresten iki farkı
 * vardır: sayfa 0'dan başlar ve tarih aralığı Türkiye saatindeki günlerin UTC'deki başlangıç ve
 * bitiş anlarıdır (`2026-11-05` → `2026-11-04T21:00:00.000Z` ile `2026-11-05T20:59:59.999Z` arası).
 */
export function toApiParams(state: SearchState): URLSearchParams {
  const params = new URLSearchParams()
  if (state.q) params.set('q', state.q)
  if (state.sources.length) params.set('sources', state.sources.join(','))
  if (state.language) params.set('language', state.language)
  if (state.categories.length) params.set('categories', state.categories.join(','))
  if (state.from) params.set('from', startOfDay(state.from).toISOString())
  if (state.to) params.set('to', endOfDay(state.to).toISOString())
  // Arama ifadesi yokken API ilgililiği yok sayar; gereksiz parametre gönderilmez.
  if (state.sort && state.q) params.set('sort', state.sort)
  params.set('page', String(state.page - 1))
  params.set('size', String(PAGE_SIZE))
  return params
}

/** Türkiye saatinde günün ilk anı. Saat farkı sabit yazılmaz; saat dilimi kurallarından hesaplanır. */
function startOfDay(day: string): Date {
  return parseDate(day).toDate(TIME_ZONE)
}

/** Türkiye saatinde günün son anı: ertesi günün ilk anından bir milisaniye önce. */
function endOfDay(day: string): Date {
  return new Date(parseDate(day).add({ days: 1 }).toDate(TIME_ZONE).getTime() - 1)
}
