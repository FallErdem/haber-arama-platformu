import { ChevronLeftIcon, ChevronRightIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { buttonVariants } from '../../components/ui/button-variants'
import { pageItems } from './pageItems'
import { MAX_PAGE } from './searchState'

interface PaginationProps {
  page: number
  totalPages: number
  hrefForPage: (page: number) => string
}

/**
 * Sayfalama (FG-AR-03): önceki/sonraki ve sayfa numaraları (`1 2 3 4 5 … 150`). Düğme değil
 * bağlantıdır: her sayfanın adresi vardır, yeni sekmede açılabilir ve paylaşılabilir. Dar ekranda
 * numaralar yerine "Sayfa 2 / 150" yazar; yedi numara 360 piksele sığmaz.
 *
 * 10.000 sonucun ötesindeki sayfalar sunulmaz; son sunulan sayfada kullanıcıya aramayı daraltması
 * önerilir (ekran akışları 5.1).
 */
export function Pagination({ page, totalPages, hrefForPage }: PaginationProps) {
  const { t } = useTranslation()
  const lastPage = Math.min(totalPages, MAX_PAGE)
  if (lastPage <= 1) {
    return null
  }
  const stepClass = buttonVariants({ variant: 'ghost' })

  return (
    <nav aria-label={t('search.pagination.label')} className="mt-8 border-t border-border pt-5">
      <div className="flex items-center justify-between gap-2">
        {page > 1 ? (
          <Link to={hrefForPage(page - 1)} rel="prev" className={stepClass}>
            <ChevronLeftIcon aria-hidden />
            {t('search.pagination.previous')}
          </Link>
        ) : (
          <span />
        )}

        <ol className="hidden items-center gap-1 sm:flex">
          {pageItems(page, lastPage).map((item, index) => (
            <li key={item === 'gap' ? `gap-${index}` : item}>
              {item === 'gap' ? (
                <span aria-hidden className="px-1 text-muted-foreground">
                  …
                </span>
              ) : item === page ? (
                <span
                  aria-current="page"
                  className="flex size-8 items-center justify-center rounded-lg bg-primary text-sm font-medium text-primary-foreground tabular-nums"
                >
                  {item}
                </span>
              ) : (
                <Link
                  to={hrefForPage(item)}
                  aria-label={t('search.pagination.page', { page: item })}
                  className={buttonVariants({ variant: 'ghost', size: 'icon', className: 'tabular-nums' })}
                >
                  {item}
                </Link>
              )}
            </li>
          ))}
        </ol>
        <p className="text-sm text-muted-foreground tabular-nums sm:hidden">
          {t('search.pagination.status', { page, total: lastPage })}
        </p>

        {page < lastPage ? (
          <Link to={hrefForPage(page + 1)} rel="next" className={stepClass}>
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

/**
 * Listenin üstündeki kısa sayfa geçişi (`‹ 2 / 150 ›`). Yeni sayfaya geçince sayfanın başına
 * dönülür; önceki ve sonraki sayfa için en alta inmek gerekmesin diye vardır. Alttaki tam sayfalama
 * olduğu gibi kalır. İlk ve son sayfada boşalan düğmenin yeri korunur; yazı kaymaz.
 */
export function PageStepper({ page, totalPages, hrefForPage }: PaginationProps) {
  const { t } = useTranslation()
  const lastPage = Math.min(totalPages, MAX_PAGE)
  if (lastPage <= 1) {
    return null
  }
  const stepClass = buttonVariants({ variant: 'ghost', size: 'icon-sm' })

  return (
    <nav aria-label={t('search.pagination.quickLabel')} className="flex items-center gap-1">
      {page > 1 ? (
        <Link to={hrefForPage(page - 1)} aria-label={t('search.pagination.previous')} className={stepClass}>
          <ChevronLeftIcon aria-hidden />
        </Link>
      ) : (
        <span aria-hidden className="size-7" />
      )}
      <span className="text-sm text-muted-foreground tabular-nums">
        <span className="sr-only">{t('search.pagination.status', { page, total: lastPage })}</span>
        <span aria-hidden>
          {page} / {lastPage}
        </span>
      </span>
      {page < lastPage ? (
        <Link to={hrefForPage(page + 1)} aria-label={t('search.pagination.next')} className={stepClass}>
          <ChevronRightIcon aria-hidden />
        </Link>
      ) : (
        <span aria-hidden className="size-7" />
      )}
    </nav>
  )
}
