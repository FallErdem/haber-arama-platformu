import { useQuery } from '@tanstack/react-query'
import { I18nProvider } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { BrowserRouter, Route, Routes } from 'react-router'
import { fetchMe } from './api/me'
import { AccessTokenContext } from './auth/accessToken'
import { CurrentUserContext } from './auth/currentUser'
import { useSessionErrors } from './auth/useSessionErrors'
import { CenteredScreen } from './components/CenteredScreen'
import { Button } from './components/ui/button'
import { AccountStatus } from './features/account/AccountStatus'
import { AdminLayout } from './features/admin/AdminLayout'
import { AuditEventsPage } from './features/admin/audit/AuditEventsPage'
import { DashboardPage } from './features/admin/dashboard/DashboardPage'
import { HiddenArticlesPage } from './features/admin/hidden/HiddenArticlesPage'
import { IngestionRunsPage } from './features/admin/runs/IngestionRunsPage'
import { SourceDetailPage } from './features/admin/sources/SourceDetailPage'
import { SourcesPage } from './features/admin/sources/SourcesPage'
import { AdminUsersPage } from './features/admin/users/AdminUsersPage'
import { ArticlePage } from './features/article/ArticlePage'
import { NotFoundPage } from './features/errors/NotFoundPage'
import { AppLayout } from './features/layout/AppLayout'
import { SavedArticlesPage } from './features/saved/SavedArticlesPage'
import { SearchPage } from './features/search/SearchPage'

interface AuthenticatedAppProps {
  accessToken: string
  onSignOut: () => void
  /** Bir istek 401 alınca çağrılır: token geçersiz veya süresi dolmuş, yeniden giriş gerekir. */
  onSessionExpired: () => void
}

/**
 * Giriş yapmış kullanıcının uygulaması. Kullanıcının durumu API'den okunur (ADR-0014): aktif değilse
 * hesap durumu ekranı, aktifse sayfalar gösterilir. Yetki kararı backend'dedir; burada yalnızca
 * hangi ekranın gösterileceği seçilir.
 */
export function AuthenticatedApp({ accessToken, onSignOut, onSessionExpired }: AuthenticatedAppProps) {
  const { t, i18n } = useTranslation()
  useSessionErrors(onSessionExpired)
  const me = useQuery({
    queryKey: ['me'],
    queryFn: () => fetchMe(accessToken),
    retry: false,
  })

  if (me.isPending) {
    return (
      <CenteredScreen>
        <p className="text-muted-foreground">{t('common.loading')}</p>
      </CenteredScreen>
    )
  }

  if (me.isError) {
    return (
      <CenteredScreen>
        <p role="alert">{t('account.loadFailed')}</p>
        <Button variant="outline" className="mt-8" onPress={onSignOut}>
          {t('logout.button')}
        </Button>
      </CenteredScreen>
    )
  }

  const { status } = me.data
  if (status !== 'ACTIVE') {
    return <AccountStatus status={status} onSignOut={onSignOut} />
  }

  // Yönlendirici yalnızca giriş tamamlandıktan sonra kurulur: girişten dönüş sayfası (/oidc-callback)
  // adres çubuğunu düzelttikten sonra açıldığı için adresi doğru okur. Sayfalar token'ı
  // AccessTokenContext'ten alır (useAccessToken). I18nProvider, React Aria bileşenlerine ve tarih/sayı
  // biçimlerine dili verir: takvimde Türkçe ay adları, haftanın Pazartesi başlaması, "1.284".
  return (
    <AccessTokenContext value={accessToken}>
      <CurrentUserContext value={me.data}>
        <I18nProvider locale={i18n.language === 'en' ? 'en-GB' : 'tr-TR'}>
          <BrowserRouter>
            <Routes>
              <Route element={<AppLayout user={me.data} onSignOut={onSignOut} />}>
                <Route index element={<SearchPage />} />
                <Route path="articles/:articleId" element={<ArticlePage />} />
                <Route path="saved" element={<SavedArticlesPage />} />
                <Route path="admin" element={<AdminLayout />}>
                  <Route index element={<DashboardPage />} />
                  <Route path="users" element={<AdminUsersPage />} />
                  <Route path="sources" element={<SourcesPage />} />
                  <Route path="sources/:sourceId" element={<SourceDetailPage />} />
                  <Route path="ingestion-runs" element={<IngestionRunsPage />} />
                  <Route path="hidden-articles" element={<HiddenArticlesPage />} />
                  <Route path="audit-events" element={<AuditEventsPage />} />
                </Route>
                <Route path="*" element={<NotFoundPage />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </I18nProvider>
      </CurrentUserContext>
    </AccessTokenContext>
  )
}
