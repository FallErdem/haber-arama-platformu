import { useQuery } from '@tanstack/react-query'
import type { Category } from '../../api/catalog'
import { fetchCategories } from '../../api/catalog'
import { useAccessToken } from '../../auth/accessToken'

/** Kaynak ve kategori listeleri nadiren değişir; 10 dakika boyunca yeniden istenmez. */
export const CATALOG_STALE_TIME = 10 * 60_000

/** Süreli etiket: haber yayımlandıktan sonra 6 saat taşır (veri modeli, kategoriler). */
export const BREAKING = 'BREAKING'

/** Hiçbir konuya uymayan haberler; ana sayfada ve kategori çubuğunda ayrı bölüm olarak gösterilmez. */
export const OTHER = 'OTHER'

/**
 * Kategori listesi (API sıralı döner, `sortOrder`). Arama filtreleri, kategori çubuğu ve ana sayfa aynı
 * önbellek kaydını kullanır; liste bir kez istenir.
 */
export function useCategories() {
  const accessToken = useAccessToken()
  return useQuery({
    queryKey: ['categories'],
    queryFn: () => fetchCategories(accessToken),
    staleTime: CATALOG_STALE_TIME,
  })
}

/** Ana sayfada ve kategori çubuğunda gösterilen konular: Son Dakika ve Diğer dışındaki konu kategorileri. */
export function featuredTopics(categories: Category[]): Category[] {
  return categories.filter((category) => category.kind === 'TOPIC' && category.code !== OTHER)
}
