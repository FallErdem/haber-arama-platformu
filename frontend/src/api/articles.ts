import { apiGet } from './client'

export type Language = 'tr' | 'en'

export interface SourceRef {
  code: string
  name: string
}

/** İmzalı görsel adresi ve ölçüleri (API sözleşmesi 4.4). */
export interface ArticleImage {
  url: string
  width: number
  height: number
}

/** Arama sonucundaki bir haber (API sözleşmesi 4.1). */
export interface ArticleSearchItem {
  id: string
  title: string
  /** Eşleşen kelimeler `<mark>` ile işaretlidir; metnin geri kalanı HTML kaçış kodlarıyla gelir. Arama ifadesi yoksa yanıtta bulunmaz. */
  highlights?: { title?: string[]; summary?: string[] }
  summary: string | null
  source: SourceRef
  language: Language
  itemType: string
  categories: string[]
  publishedAt: string
  url: string
  image: ArticleImage | null
  otherSourcesCount: number
  /** Haberin oturumdaki kullanıcı tarafından kaydedilip kaydedilmediği. */
  saved: boolean
}

/** Arama yanıtı: sayfalı liste (API sözleşmesi 2.4). `page` 0'dan başlar. */
export interface ArticleSearchResponse {
  items: ArticleSearchItem[]
  page: number
  size: number
  totalElements: number
  totalPages: number
  /** `eq`: sayı kesin; `gte`: gerçek sayı daha büyük olabilir (en fazla 10.000 sayılır). */
  totalRelation: 'eq' | 'gte'
}

/** Haber detayı (API sözleşmesi 4.2). */
export interface ArticleDetail {
  id: string
  title: string
  summary: string | null
  /** İşçinin temizlediği HTML; kaynak vermiyorsa `null`. */
  content: string | null
  author: string | null
  url: string
  source: SourceRef & { homepageUrl: string; attributionText: string | null }
  language: Language
  itemType: string
  categories: string[]
  publishedAt: string
  media: (ArticleImage & { caption: string | null; credit: string | null })[]
  otherSources: { articleId: string; source: SourceRef; url: string }[]
  saved: boolean
}

/** Arama. `query`, API'nin parametrelerini taşır (bkz. `toApiParams`). */
export function searchArticles(accessToken: string, query: URLSearchParams): Promise<ArticleSearchResponse> {
  return apiGet<ArticleSearchResponse>('/api/v1/articles', accessToken, query)
}

export function fetchArticle(accessToken: string, articleId: string): Promise<ArticleDetail> {
  return apiGet<ArticleDetail>(`/api/v1/articles/${encodeURIComponent(articleId)}`, accessToken)
}
