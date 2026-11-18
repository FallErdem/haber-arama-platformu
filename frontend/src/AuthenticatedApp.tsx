import { useQuery } from '@tanstack/react-query'
import { I18nProvider } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { BrowserRouter, Route, Routes } from 'react-router'
import { fetchMe } from './api/me'
import { AccessTokenContext } from './auth/accessToken'
import { CenteredScreen } from './components/CenteredScreen'
import { Button } from './components/ui/button'
import { AccountStatus } from './features/account/AccountStatus'
import { NotFoundPage } from './features/errors/NotFoundPage'
import { AppLayout } from './features/layout/AppLayout'
import { SearchPage } from './features/search/SearchPage'

interface AuthenticatedAppProps {
  accessToken: string
  onSignOut: () => void
}

/**
 * Giriş yapmış kullanıcının uygulaması. Kullanıcının durumu API'den okunur (ADR-0014): aktif değilse
 * hesap durumu ekranı, aktifse sayfalar gösterilir. Yetki kararı backend'dedir; burada yalnızca
 * hangi ekranın gösterileceği seçilir.
 */
export function AuthenticatedApp({ accessToken, onSignOut }: AuthenticatedAppProps) {
  const { t, i18n } = useTranslation()
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
      <I18nProvider locale={i18n.language === 'en' ? 'en-GB' : 'tr-TR'}>
        <BrowserRouter>
          <Routes>
            <Route element={<AppLayout user={me.data} onSignOut={onSignOut} />}>
              <Route index element={<SearchPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </I18nProvider>
    </AccessTokenContext>
  )
}
