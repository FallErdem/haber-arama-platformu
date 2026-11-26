import { cn } from 'cn'
import { useTranslation } from 'react-i18next'
import { Link, NavLink, Outlet, useLocation } from 'react-router'
import type { Me } from '../../api/me'
import { Logo } from '../../components/Logo'
import { Button } from '../../components/ui/button'
import { BackToTop } from './BackToTop'
import { ReadingHistory } from './ReadingHistory'
import { CategoryBar } from './CategoryBar'
import { ThemeToggle } from './ThemeToggle'

interface AppLayoutProps {
  user: Me
  onSignOut: () => void
}

/**
 * Aktif kullanıcının bütün sayfalarının ortak çerçevesi: üst çubuk ve sayfanın içeriği. Sayfalar
 * `<Outlet />` yerine çizilir; üst çubuk sayfa değişince yeniden çizilmez.
 *
 * Uygulamanın adı ana sayfaya (aramaya) götürür. Üst menü (ekran akışları 3. bölüm): Arama,
 * Kaydedilenler ve yalnızca yöneticiye Yönetim. Dar ekranda menü ikinci satıra iner; üst çubuk 360
 * piksele sığar (FOG-34).
 */
export function AppLayout({ user, onSignOut }: AppLayoutProps) {
  const { t } = useTranslation()
  const { pathname } = useLocation()
  // Okuma geçmişi haber sayfalarında görünür; yönetim panelinde işe yaramaz. Kategori çubuğu yalnızca arama ve
  // haber sayfalarında: Kaydedilenler kendi listesidir, kategoriye göre süzülmez.
  const isAdminPage = pathname.startsWith('/admin')
  const showCategoryBar = !isAdminPage && !pathname.startsWith('/saved')
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

      {/*
        Sayfalar ortalanmaz, sola yaslıdır. Üst çubuk ekranın tamamına yayılır: ad ve menü solda, çıkış sağ
        kenarda. Sayfaların genişliği farklı olduğu için (arama ve yönetim) üst çubuk birine göre sınırlanmaz.
      */}
      <header className="border-b border-border">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-1 px-4 py-2.5 sm:h-14 sm:flex-nowrap sm:py-0 sm:px-6">
          <Link to="/" className="flex items-center gap-2 font-heading text-lg font-semibold tracking-tight sm:text-xl">
            <Logo className="size-7 shrink-0" />
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
              {/* Yalnızca yöneticiye görünür; yalnızca bir kolaylıktır, yetki kontrolü backend'dedir. */}
              {user.role === 'ADMIN' && (
                <li>
                  {/* /admin altındaki her ekranda (kullanıcılar, kaynaklar, geçmiş) etkin görünür. */}
                  <NavLink to="/admin" className={navClass}>
                    {t('nav.admin')}
                  </NavLink>
                </li>
              )}
            </ul>
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
            {/* Dar ekranlarda ad gizlenir; üst çubuk 360 piksele sığar (FOG-34). */}
            <span className="hidden text-sm text-muted-foreground sm:inline">{user.displayName ?? user.email}</span>
            <Button variant="ghost" size="sm" onPress={onSignOut}>
              {t('logout.button')}
            </Button>
          </div>
        </div>
      </header>
      {showCategoryBar && <CategoryBar />}

      <div className="flex flex-1">
        {/* tabIndex={-1}: "İçeriğe geç" bağlantısıyla gelen odak bu alana taşınabilsin. */}
        <main id="main-content" tabIndex={-1} className="min-w-0 flex-1 outline-none">
          <Outlet />
        </main>
        {/* Haber sayfalarında geniş ekranın sağında okuma geçmişi; kaydırılınca da görünür kalır (sticky). */}
        {!isAdminPage && (
          <aside className="hidden w-80 shrink-0 border-l border-border px-6 py-10 lg:block">
            <div className="sticky top-6">
              <ReadingHistory />
            </div>
          </aside>
        )}
      </div>
      <BackToTop />
    </div>
  )
}
