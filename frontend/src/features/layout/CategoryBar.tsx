import { cn } from 'cn'
import { useTranslation } from 'react-i18next'
import { Link, useLocation } from 'react-router'
import { BREAKING, featuredTopics, useCategories } from '../search/useCategories'

/**
 * Üst çubuğun altındaki kategori menüsü: Son Dakika ve konu kategorileri. Her bağlantı aramayı o kategoriyle
 * açar (`/?categories=SPORTS`); filtre menüsünü açmadan tek tıkla gezilir. Dar ekranda yana kayar.
 *
 * Bulunulan kategori, adreste yalnızca o kategori seçiliyse işaretlenir (`aria-current`); başka bir filtre veya
 * arama ifadesi de varsa sayfa artık o kategorinin listesi değildir.
 */
export function CategoryBar() {
  const { t } = useTranslation()
  const location = useLocation()
  const categories = useCategories()
  const params = new URLSearchParams(location.search)
  const current = location.pathname === '/' && params.size === 1 ? params.get('categories') : null

  const linkClass = (code: string) =>
    cn(
      'block shrink-0 rounded-md px-2.5 py-1.5 text-sm whitespace-nowrap transition-colors hover:bg-muted hover:text-foreground',
      current === code ? 'bg-muted font-medium text-foreground' : 'text-muted-foreground',
    )

  const codes = [BREAKING, ...featuredTopics(categories.data ?? []).map((category) => category.code)]

  return (
    <nav aria-label={t('nav.categories')} className="border-b border-border">
      {/* Kenar boşluğu bağlantıların iç boşluğu (px-2.5) kadar azdır: ilk kategorinin yazısı, üst çubuktaki
          uygulama adıyla aynı hizada başlar. */}
      <ul className="flex gap-1 overflow-x-auto px-1.5 py-1.5 sm:px-3.5">
        {codes.map((code) => (
          <li key={code}>
            <Link
              to={`/?categories=${code}`}
              aria-current={current === code ? 'page' : undefined}
              className={linkClass(code)}
            >
              {t(`categories.${code}`)}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  )
}
