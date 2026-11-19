import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { cn } from 'cn'
import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router'
import { z } from 'zod'
import { fetchSavedArticles } from '../../api/savedArticles'
import { useAccessToken } from '../../auth/accessToken'
import { Button } from '../../components/ui/button'
import { Pagination } from '../search/Pagination'
import { SavedItem } from './SavedItem'

/** Adresteki sayfa numarası 1'den başlar; geçersiz değer (`?page=abc`, `?page=0`) ilk sayfa sayılır. */
const pageSchema = z.coerce.number().int().min(1).catch(1)

const hrefForPage = (page: number) => (page === 1 ? '/saved' : `/saved?page=${page}`)

/**
 * Kaydedilenler (ekran akışları 5.1; FG-KO-02, FG-KO-03): kaydedilme zamanına göre yeniden eskiye,
 * sayfalı. Sayfa numarası aramadaki gibi adreste tutulur; geri düğmesi ve yenileme aynı sayfayı açar.
 */
export function SavedArticlesPage() {
  const { t } = useTranslation()
  const accessToken = useAccessToken()
  const [params] = useSearchParams()
  const page = pageSchema.parse(params.get('page') ?? undefined)

  const saved = useQuery({
    queryKey: ['saved-articles', page],
    // API'de sayfalar 0'dan başlar.
    queryFn: () => fetchSavedArticles(accessToken, page - 1),
    placeholderData: keepPreviousData,
  })

  // Sayfa değişince sayfanın başına dönülür; ilk açılışta dokunulmaz (arama sayfasıyla aynı).
  const previousPage = useRef(page)
  useEffect(() => {
    if (previousPage.current !== page) {
      previousPage.current = page
      window.scrollTo({ top: 0 })
    }
  }, [page])

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 sm:py-10">
      <h1 className="mb-5 text-3xl font-semibold tracking-tight">{t('saved.title')}</h1>

      {saved.isPending ? (
        <p className="mt-10 text-muted-foreground">{t('saved.loading')}</p>
      ) : saved.isError ? (
        <div role="alert" className="mt-10">
          <p>{t('saved.loadFailed')}</p>
          <Button variant="outline" className="mt-4" onPress={() => void saved.refetch()}>
            {t('saved.retry')}
          </Button>
        </div>
      ) : saved.data.items.length === 0 ? (
        <EmptySaved isPageEmpty={saved.data.totalElements > 0} />
      ) : (
        <>
          <ol
            aria-busy={saved.isFetching}
            className={cn(
              'divide-y divide-border border-t border-border transition-opacity',
              saved.isPlaceholderData && 'opacity-50',
            )}
          >
            {saved.data.items.map((item) => (
              <li key={item.articleId}>
                <SavedItem item={item} />
              </li>
            ))}
          </ol>
          <Pagination page={page} totalPages={saved.data.totalPages} hrefForPage={hrefForPage} />
        </>
      )}
    </div>
  )
}

function EmptySaved({ isPageEmpty }: { isPageEmpty: boolean }) {
  const { t } = useTranslation()
  const linkClass = 'mt-3 inline-block text-primary underline-offset-4 hover:underline'

  // Kayıt var ama bu sayfada yok: sayfanın son haberi çıkarıldı ya da adrese olmayan bir sayfa yazıldı.
  if (isPageEmpty) {
    return (
      <div className="py-16 text-center">
        <p className="text-muted-foreground">{t('saved.pageEmpty')}</p>
        <Link to={hrefForPage(1)} className={linkClass}>
          {t('saved.firstPage')}
        </Link>
      </div>
    )
  }
  return (
    <div className="py-16 text-center">
      <p className="text-muted-foreground">{t('saved.empty')}</p>
      <p className="mt-1 text-sm text-muted-foreground">{t('saved.emptyHint')}</p>
      <Link to="/" className={linkClass}>
        {t('saved.goToSearch')}
      </Link>
    </div>
  )
}
