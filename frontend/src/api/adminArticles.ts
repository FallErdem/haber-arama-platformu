import { apiGet, apiSendJson } from './client'

/** Yönetim panelindeki bir haber (API sözleşmesi 6.6). Gizli değilse gizleme alanları `null`'dır. */
export interface AdminArticle {
  id: string
  title: string
  /** Haberin kaynağındaki adresi. */
  url: string
  sourceCode: string
  sourceName: string
  publishedAt: string
  hidden: boolean
  hiddenAt: string | null
  hiddenReason: string | null
  hiddenBy: string | null
  hiddenByEmail: string | null
}

export interface AdminArticlesResponse {
  items: AdminArticle[]
  page: number
  size: number
  totalElements: number
  totalPages: number
}

const ARTICLES = '/api/v1/admin/articles'

/** Haber listesi. `query`: `hidden`, `sources`, `from`, `to`, `page` (0'dan başlar). */
export function fetchAdminArticles(accessToken: string, query: URLSearchParams): Promise<AdminArticlesResponse> {
  return apiGet<AdminArticlesResponse>(ARTICLES, accessToken, query)
}

/** Haberi gerekçesiyle gizler (FG-YP-09). */
export function hideArticle(accessToken: string, articleId: string, reason: string): Promise<AdminArticle> {
  return apiSendJson<AdminArticle>('POST', `${ARTICLES}/${encodeURIComponent(articleId)}/hide`, accessToken, {
    reason,
  })
}

export function unhideArticle(accessToken: string, articleId: string): Promise<AdminArticle> {
  return apiSendJson<AdminArticle>('POST', `${ARTICLES}/${encodeURIComponent(articleId)}/unhide`, accessToken)
}
