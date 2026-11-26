import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { searchArticles, type ArticleDetail } from '../../api/articles'
import { useAccessToken } from '../../auth/accessToken'
import { ArticleCard } from '../home/ArticleCard'
import { BREAKING, OTHER } from '../search/useCategories'

/** Gösterilen ilgili haber sayısı. Haberin kendisi de gelebileceği için bir fazlası istenir. */
const RELATED_COUNT = 4

/**
 * Metnin altındaki "İlgili haberler": haberin ilk konu kategorisindeki en yeni haberler (kendisi hariç). Okur
 * haberi bitirince siteden çıkmak yerine devam edebilir. Konu kategorisi yoksa (yalnızca Son Dakika veya Diğer)
 * ya da başka haber yoksa bölüm gösterilmez.
 */
export function RelatedArticles({ article }: { article: ArticleDetail }) {
  const { t } = useTranslation()
  const accessToken = useAccessToken()
  const category = article.categories.find((code) => code !== BREAKING && code !== OTHER)
  const related = useQuery({
    queryKey: ['related', article.id],
    queryFn: () =>
      searchArticles(accessToken, new URLSearchParams({ categories: category!, size: String(RELATED_COUNT + 1) })),
    enabled: category !== undefined,
  })

  const items = (related.data?.items ?? []).filter((item) => item.id !== article.id).slice(0, RELATED_COUNT)
  if (items.length === 0) {
    return null
  }

  return (
    <section aria-labelledby="related-articles" className="mt-12 border-t border-border pt-8">
      <h2 id="related-articles" className="text-lg font-semibold">
        {t('article.related')}
      </h2>
      <div className="mt-4 grid grid-cols-2 gap-x-5 gap-y-7">
        {items.map((item) => (
          <ArticleCard key={item.id} item={item} />
        ))}
      </div>
    </section>
  )
}
