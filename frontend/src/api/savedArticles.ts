import type { ArticleImage, SourceRef } from './articles'
import { apiGet, apiSend } from './client'

/** Kaydedilen haberler listesindeki bir öğe (API sözleşmesi 5.1). */
export interface SavedArticleItem {
  articleId: string
  savedAt: string
  /** Haber kaydedildikten sonra yönetici tarafından gizlendiyse `true`; `article` o zaman `null`'dır. */
  hidden: boolean
  article: {
    title: string
    source: SourceRef
    publishedAt: string
    image: ArticleImage | null
  } | null
}

/** Sayfalı liste (API sözleşmesi 2.4). `page` 0'dan başlar. */
export interface SavedArticlesResponse {
  items: SavedArticleItem[]
  page: number
  size: number
  totalElements: number
  totalPages: number
}

const PATH = '/api/v1/me/saved-articles'

/** Kaydedilen haberler, kaydedilme zamanına göre yeniden eskiye. `page` 0'dan başlar. */
export function fetchSavedArticles(accessToken: string, page: number): Promise<SavedArticlesResponse> {
  return apiGet<SavedArticlesResponse>(PATH, accessToken, new URLSearchParams({ page: String(page) }))
}

/** Haberi kaydeder; zaten kayıtlıysa bir şey değişmez. */
export function saveArticle(accessToken: string, articleId: string): Promise<void> {
  return apiSend('PUT', `${PATH}/${encodeURIComponent(articleId)}`, accessToken)
}

/** Haberi kayıttan çıkarır; kayıtlı değilse bir şey değişmez. */
export function unsaveArticle(accessToken: string, articleId: string): Promise<void> {
  return apiSend('DELETE', `${PATH}/${encodeURIComponent(articleId)}`, accessToken)
}
