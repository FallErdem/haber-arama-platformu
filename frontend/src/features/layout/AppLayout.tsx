import { cn } from 'cn'
import { useTranslation } from 'react-i18next'
import { Link, NavLink, Outlet } from 'react-router'
import type { Me } from '../../api/me'
import { Button } from '../../components/ui/button'

interface AppLayoutProps {
  user: Me
  onSignOut: () => void
}

/**
 * Aktif kullanıcının bütün sayfalarının ortak çerçevesi: üst çubuk ve sayfanın içeriği. Sayfalar
 * `<Outlet />` yerine çizilir; üst çubuk sayfa değişince yeniden çizilmez.
 *
 * Uygulamanın adı ana sayfaya (aramaya) götürür. Üst menü (ekran akışları 3. bölüm): Arama ve
 * Kaydedilenler. Dar ekranda menü ikinci satıra iner; üst çubuk 360 piksele sığar (FOG-34).
 */
export function AppLayout({ user, onSignOut }: AppLayoutProps) {
  const { t } = useTranslation()
  // NavLink, bulunulan sayfanın bağlantısına aria-current="page" ekler; stil de buna göre seçilir.
  const navClass = ({ isActive }: { isActive: boolean }) =>
    cn(
      'rounded-md py-1 text-sm transition-colors hover:text-foreground',
      isActive ? 'font-medium text-foreground' : 'text-muted-foreground',
    )

  return (
    <div className="flex min-h-dvh flex-col">
      {/* Klavyeyle gezenler için ilk odak: üst çubuğu atlayıp doğrudan içeriğe geçer (WCAG 2.4.1). Odaklanınca görünür. */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-50 focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:ring-3 focus:ring-ring/50"
      >
        {t('layout.skipToContent')}
      </a>

      <header className="border-b border-border">
        <div className="mx-auto flex max-w-4xl flex-wrap items-center gap-x-6 gap-y-1 px-4 py-2.5 sm:h-14 sm:flex-nowrap sm:py-0 sm:px-6">
          <Link to="/" className="font-heading text-lg font-semibold tracking-tight sm:text-xl">
            {t('app.title')}
          </Link>

          <nav aria-label={t('nav.label')} className="order-last w-full sm:order-none sm:w-auto">
            <ul className="flex items-center gap-5">
              <li>
                {/* end: "/" adresi yalnızca ana sayfadayken etkin sayılır; her adres "/" ile başlar. */}
                <NavLink to="/" end className={navClass}>
                  {t('nav.search')}
                </NavLink>
              </li>
              <li>
                <NavLink to="/saved" className={navClass}>
                  {t('nav.saved')}
                </NavLink>
              </li>
            </ul>
          </nav>

          <div className="ml-auto flex items-center gap-2">
            {/* Dar ekranlarda ad gizlenir; üst çubuk 360 piksele sığar (FOG-34). */}
            <span className="hidden text-sm text-muted-foreground sm:inline">{user.displayName ?? user.email}</span>
            <Button variant="ghost" size="sm" onPress={onSignOut}>
              {t('logout.button')}
            </Button>
          </div>
        </div>
      </header>

      {/* tabIndex={-1}: "İçeriğe geç" bağlantısıyla gelen odak bu alana taşınabilsin. */}
      <main id="main-content" tabIndex={-1} className="flex-1 outline-none">
        <Outlet />
      </main>
    </div>
  )
}
