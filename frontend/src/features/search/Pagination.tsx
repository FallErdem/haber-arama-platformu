import { ChevronLeftIcon, ChevronRightIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { buttonVariants } from '../../components/ui/button-variants'
import { MAX_PAGE } from './searchState'

interface PaginationProps {
  page: number
  totalPages: number
  hrefForPage: (page: number) => string
}

/**
 * Önceki/sonraki sayfa bağlantıları (FG-AR-03). Düğme değil bağlantıdır: sayfanın adresi vardır, yeni
 * sekmede açılabilir ve paylaşılabilir. 10.000 sonucun ötesindeki sayfalar sunulmaz; son sunulan
 * sayfada kullanıcıya aramayı daraltması önerilir (ekran akışları 5.1).
 */
export function Pagination({ page, totalPages, hrefForPage }: PaginationProps) {
  const { t } = useTranslation()
  const lastPage = Math.min(totalPages, MAX_PAGE)
  if (lastPage <= 1) {
    return null
  }
  const linkClass = buttonVariants({ variant: 'outline' })

  return (
    <nav aria-label={t('search.pagination.label')} className="mt-8 border-t border-border pt-5">
      <div className="flex items-center justify-between gap-4">
        {page > 1 ? (
          <Link to={hrefForPage(page - 1)} rel="prev" className={linkClass}>
            <ChevronLeftIcon aria-hidden />
            {t('search.pagination.previous')}
          </Link>
        ) : (
          <span />
        )}
        <p className="text-sm text-muted-foreground tabular-nums">
          {t('search.pagination.status', { page, total: lastPage })}
        </p>
        {page < lastPage ? (
          <Link to={hrefForPage(page + 1)} rel="next" className={linkClass}>
            {t('search.pagination.next')}
            <ChevronRightIcon aria-hidden />
          </Link>
        ) : (
          <span />
        )}
      </div>
      {totalPages > MAX_PAGE && page === lastPage && (
        <p className="mt-4 text-center text-sm text-muted-foreground">{t('search.pagination.limit')}</p>
      )}
    </nav>
  )
}
