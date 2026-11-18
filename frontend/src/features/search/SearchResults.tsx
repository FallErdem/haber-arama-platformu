import type { UseQueryResult } from '@tanstack/react-query'
import { cn } from 'cn'
import type { Key } from 'react-aria-components'
import { useLocale } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import type { ArticleSearchResponse } from '../../api/articles'
import { Button } from '../../components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { PageStepper, Pagination } from './Pagination'
import { ResultItem } from './ResultItem'
import type { SearchSort, SearchState } from './searchState'

interface SearchResultsProps {
  state: SearchState
  results: UseQueryResult<ArticleSearchResponse>
  onChange: (changes: Partial<SearchState>) => void
  onClearFilters: () => void
  hrefForPage: (page: number) => string
}

/** Sonuç sayısı, sıralama, sonuç listesi ve sayfalama. */
export function SearchResults({ state, results, onChange, onClearFilters, hrefForPage }: SearchResultsProps) {
  const { t } = useTranslation()
  const { locale } = useLocale()

  if (results.isPending) {
    return <p className="mt-10 text-muted-foreground">{t('search.loading')}</p>
  }

  if (results.isError) {
    return (
      <div role="alert" className="mt-10">
        <p>{t('search.loadFailed')}</p>
        <Button variant="outline" className="mt-4" onPress={() => void results.refetch()}>
          {t('search.retry')}
        </Button>
      </div>
    )
  }

  const { items, totalElements, totalPages, totalRelation } = results.data
  const formatted = new Intl.NumberFormat(locale).format(totalElements)
  const countText =
    totalRelation === 'gte'
      ? t('search.resultCountAtLeast', { formatted })
      : t('search.resultCount', { count: totalElements, formatted })

  return (
    <section className="mt-8">
      <div className="flex min-h-9 flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-border pb-3">
        {/* aria-live: sayı değişince ekran okuyucu yeni sonucu duyurur. */}
        <p aria-live="polite" className="text-sm text-muted-foreground tabular-nums">
          {countText}
        </p>
        <div className="flex items-center gap-2">
          {/* Arama ifadesi yokken ilgililik hesaplanamaz; haberler yalnızca tarihe göre sıralanır. */}
          {state.q && <SortSelect value={state.sort ?? 'relevance'} onChange={(sort) => onChange({ sort })} />}
          <PageStepper page={state.page} totalPages={totalPages} hrefForPage={hrefForPage} />
        </div>
      </div>

      {items.length === 0 ? (
        <EmptyResults isPageEmpty={totalElements > 0} onClearFilters={onClearFilters} hrefFirstPage={hrefForPage(1)} />
      ) : (
        // Yeni sayfa yüklenirken eski sonuçlar soluk gösterilir; ekran boş kalmaz.
        <ol
          aria-busy={results.isFetching}
          className={cn('divide-y divide-border transition-opacity', results.isPlaceholderData && 'opacity-50')}
        >
          {items.map((item) => (
            <li key={item.id}>
              <ResultItem item={item} />
            </li>
          ))}
        </ol>
      )}

      <Pagination page={state.page} totalPages={totalPages} hrefForPage={hrefForPage} />
    </section>
  )
}

function SortSelect({ value, onChange }: { value: SearchSort; onChange: (sort: SearchSort) => void }) {
  const { t } = useTranslation()

  return (
    <Select
      aria-label={t('search.sort.label')}
      value={value}
      onChange={(key: Key | null) => onChange(key === 'newest' ? 'newest' : 'relevance')}
    >
      <SelectTrigger className="w-auto border-transparent">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem id="relevance">{t('search.sort.relevance')}</SelectItem>
        <SelectItem id="newest">{t('search.sort.newest')}</SelectItem>
      </SelectContent>
    </Select>
  )
}

function EmptyResults({
  isPageEmpty,
  onClearFilters,
  hrefFirstPage,
}: {
  isPageEmpty: boolean
  onClearFilters: () => void
  hrefFirstPage: string
}) {
  const { t } = useTranslation()

  // Sonuç var ama bu sayfada yok: adreste var olmayan bir sayfa numarası yazılmıştır.
  if (isPageEmpty) {
    return (
      <div className="py-16 text-center">
        <p className="text-muted-foreground">{t('search.pageEmpty')}</p>
        <Link to={hrefFirstPage} className="mt-3 inline-block text-primary underline-offset-4 hover:underline">
          {t('search.firstPage')}
        </Link>
      </div>
    )
  }
  return (
    <div className="py-16 text-center">
      <p className="text-muted-foreground">{t('search.empty')}</p>
      <Button variant="link" className="mt-2" onPress={onClearFilters}>
        {t('search.filters.clear')}
      </Button>
    </div>
  )
}
