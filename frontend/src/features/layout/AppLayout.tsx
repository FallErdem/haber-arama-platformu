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
 * Aktif kullanıcının bütün sayfalarının ortak çerçevesi: üst menü ve sayfanın içeriği. Sayfalar
 * `<Outlet />` yerine çizilir; menü sayfa değişince yeniden çizilmez.
 */
export function AppLayout({ user, onSignOut }: AppLayoutProps) {
  const { t } = useTranslation()

  return (
    <div className="flex min-h-dvh flex-col">
      {/* Klavyeyle gezenler için ilk odak: menüyü atlayıp doğrudan içeriğe geçer (WCAG 2.4.1). Odaklanınca görünür. */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-50 focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:ring-3 focus:ring-ring/50"
      >
        {t('layout.skipToContent')}
      </a>

      <header className="border-b border-border">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4 sm:px-6">
          <Link to="/" className="font-heading text-xl font-semibold tracking-tight">
            {t('app.brand')}
          </Link>

          <nav aria-label={t('nav.label')}>
            {/* NavLink, bulunulan sayfanın bağlantısına aria-current="page" ekler; ekran okuyucu bunu okur. */}
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                cn(
                  'text-sm transition-colors hover:text-foreground',
                  isActive ? 'font-medium text-foreground' : 'text-muted-foreground',
                )
              }
            >
              {t('nav.search')}
            </NavLink>
          </nav>

          <div className="ml-auto flex items-center gap-2">
            {/* Dar ekranlarda ad gizlenir; menü 360 piksele sığar (FOG-34). */}
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
