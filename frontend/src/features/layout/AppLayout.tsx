import { useTranslation } from 'react-i18next'
import { Link, Outlet } from 'react-router'
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
 * Uygulamanın adı ana sayfaya (aramaya) götürür. Üst menü (ekran akışları 3. bölüm) ikinci bir öğe
 * geldiğinde (Kaydedilenler, İ-20) eklenecek; tek öğeli bir menü adın tekrarı gibi duruyordu.
 */
export function AppLayout({ user, onSignOut }: AppLayoutProps) {
  const { t } = useTranslation()

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
        <div className="mx-auto flex h-14 max-w-4xl items-center gap-6 px-4 sm:px-6">
          <Link to="/" className="font-heading text-lg font-semibold tracking-tight sm:text-xl">
            {t('app.title')}
          </Link>

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
