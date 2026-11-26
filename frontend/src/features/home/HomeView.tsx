import { useIsFetching, useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCwIcon } from 'lucide-react'
import { useState } from 'react'
import { useLocale } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { searchArticles } from '../../api/articles'
import { useAccessToken } from '../../auth/accessToken'
import { Button } from '../../components/ui/button'
import { featuredTopics, useCategories } from '../search/useCategories'
import { ArticleCard } from './ArticleCard'
import { Headline } from './Headline'
import { HOME_QUERY_KEY } from './queryKeys'

/** Her kategori bölümünde gösterilen haber sayısı: 2, 3 ve 6 sütunlu ızgaraya boşluksuz oturur. */
const CARDS_PER_SECTION = 6

/**
 * Ana sayfa (adreste arama veya filtre yokken): her konu kategorisinin en yeni haberleri, görselli kartlarla.
 * Haberler sürekli geldiği için sayfa açıkken bölümler kendiliğinden değişmez (okunan kart yerinden kaymaz);
 * kullanıcı "Yenile" ile günceller, sayfayı yeniden yüklemesi gerekmez.
 */
export function HomeView() {
  const { t } = useTranslation()
  const { locale } = useLocale()
  const queryClient = useQueryClient()
  const categories = useCategories()
  const isRefreshing = useIsFetching({ queryKey: [HOME_QUERY_KEY] }) > 0
  const [updatedAt, setUpdatedAt] = useState(() => new Date())

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: [HOME_QUERY_KEY] })
    setUpdatedAt(new Date())
  }

  return (
    <div className="mt-10">
      <Headline />

      <div className="mt-10 flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-border pb-3">
        <h2 className="text-xl font-semibold tracking-tight">{t('home.heading')}</h2>
        <div className="flex items-center gap-3">
          {/* aria-live: yenileme bitince ekran okuyucu yeni saati duyurur. */}
          <p aria-live="polite" className="text-xs text-muted-foreground tabular-nums">
            {t('home.updatedAt', {
              time: new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit' }).format(updatedAt),
            })}
          </p>
          <Button variant="outline" size="sm" onPress={() => void refresh()} isDisabled={isRefreshing}>
            {/* Hareketi azaltma ayarı açıksa simge dönmez. */}
            <RefreshCwIcon aria-hidden className={isRefreshing ? 'animate-spin motion-reduce:animate-none' : ''} />
            {t('home.refresh')}
          </Button>
        </div>
      </div>

      {categories.isError ? (
        <p role="alert" className="mt-8 text-muted-foreground">
          {t('home.loadFailed')}
        </p>
      ) : (
        featuredTopics(categories.data ?? []).map((category) => (
          <CategorySection key={category.code} code={category.code} />
        ))
      )}

      <p className="mt-12">
        <Link to="/?sort=newest" className="text-sm font-medium text-primary underline-offset-4 hover:underline">
          {t('home.allNews')}
        </Link>
      </p>
    </div>
  )
}

/** Bir kategorinin en yeni haberleri. Haberi olmayan kategori hiç gösterilmez. */
function CategorySection({ code }: { code: string }) {
  const { t } = useTranslation()
  const accessToken = useAccessToken()
  const articles = useQuery({
    queryKey: [HOME_QUERY_KEY, 'category', code],
    queryFn: () =>
      searchArticles(accessToken, new URLSearchParams({ categories: code, size: String(CARDS_PER_SECTION) })),
    // Sayfa açıkken kendiliğinden yeniden istenmez; yalnızca Yenile düğmesi günceller.
    staleTime: Infinity,
  })
  const name = t(`categories.${code}`)

  if (articles.isSuccess && articles.data.items.length === 0) {
    return null
  }

  return (
    <section aria-labelledby={`home-${code}`} className="mt-10">
      <div className="flex items-baseline justify-between gap-4">
        <h3 id={`home-${code}`} className="text-lg font-semibold">
          {name}
        </h3>
        <Link
          to={`/?categories=${code}`}
          aria-label={t('home.seeAllIn', { category: name })}
          className="text-sm text-primary underline-offset-4 hover:underline"
        >
          {t('home.seeAll')}
        </Link>
      </div>
      {articles.isError ? (
        <div role="alert" className="mt-4 text-sm text-muted-foreground">
          {t('home.sectionFailed')}{' '}
          <Button variant="link" size="sm" className="px-0" onPress={() => void articles.refetch()}>
            {t('search.retry')}
          </Button>
        </div>
      ) : (
        <div className="mt-4 grid grid-cols-2 gap-x-5 gap-y-7 md:grid-cols-3 2xl:grid-cols-6">
          {articles.isPending
            ? Array.from({ length: CARDS_PER_SECTION }, (_, index) => <CardPlaceholder key={index} />)
            : articles.data.items.map((item) => <ArticleCard key={item.id} item={item} />)}
        </div>
      )}
    </section>
  )
}

/** Yüklenirken kartın yerini tutar; sayfa yüklenince kaymaz. */
function CardPlaceholder() {
  return (
    <div aria-hidden className="animate-pulse motion-reduce:animate-none">
      <div className="aspect-[16/10] w-full rounded-sm bg-muted" />
      <div className="mt-3 h-3 w-1/2 rounded-sm bg-muted" />
      <div className="mt-2 h-4 w-full rounded-sm bg-muted" />
      <div className="mt-1.5 h-4 w-3/4 rounded-sm bg-muted" />
    </div>
  )
}
