import type { Language } from './articles'
import { apiGet } from './client'

/** Etkin bir kaynak (API sözleşmesi 4.3). */
export interface Source {
  code: string
  name: string
  language: Language
}

/** Kategori. Görünen adı yanıtta yoktur; arayüz dil dosyalarından koda göre bulur (FOG-31). */
export interface Category {
  code: string
  /** `TOPIC`: konu; `TEMPORAL`: Son Dakika gibi süreli etiket. */
  kind: 'TOPIC' | 'TEMPORAL'
  sortOrder: number
}

/** Sayfalanmayan listeler de öğelerini `items` alanında taşır (API sözleşmesi 2.4). */
interface ItemList<T> {
  items: T[]
}

export async function fetchSources(accessToken: string): Promise<Source[]> {
  return (await apiGet<ItemList<Source>>('/api/v1/sources', accessToken)).items
}

export async function fetchCategories(accessToken: string): Promise<Category[]> {
  return (await apiGet<ItemList<Category>>('/api/v1/categories', accessToken)).items
}
