import { useTranslation } from 'react-i18next'
import { useAuth } from 'react-oidc-context'
import { AuthenticatedApp } from './AuthenticatedApp'
import { currentReturnPath } from './auth/returnPath'
import { useSilentLogin } from './auth/useSilentLogin'
import { CenteredScreen } from './components/CenteredScreen'
import { Button } from './components/ui/button'

export default function App() {
  const auth = useAuth()
  const { t } = useTranslation()
  const isSilentLoginDone = useSilentLogin(auth)

  if (auth.isLoading || !isSilentLoginDone) {
    return (
      <CenteredScreen>
        <p className="text-muted-foreground">{t('common.loading')}</p>
      </CenteredScreen>
    )
  }

  if (auth.isAuthenticated && auth.user) {
    return (
      <AuthenticatedApp
        accessToken={auth.user.access_token}
        onSignOut={() => void auth.signoutRedirect()}
        // Keycloak oturumu sürüyorsa yönlendirme şifre sormadan geri döner; kullanıcı aynı adrese döner.
        onSessionExpired={() => void auth.signinRedirect({ state: currentReturnPath() })}
      />
    )
  }

  // Sessiz giriş denemesinin başarısız olması olağandır (kullanıcı henüz giriş
  // yapmamıştır); yalnızca kullanıcının başlattığı girişin hatası gösterilir.
  const hasLoginFailed = auth.error !== undefined && auth.error.source !== 'signinSilent'

  return (
    <CenteredScreen>
      <h1 className="text-4xl font-semibold tracking-tight">{t('app.title')}</h1>
      <p className="mt-3 text-muted-foreground">{t('login.intro')}</p>
      {hasLoginFailed && (
        <p role="alert" className="mt-6 text-sm text-destructive">
          {t('login.failed')}
        </p>
      )}
      {/* Kullanıcının bulunduğu adres girişe `state` olarak verilir; girişten sonra oraya dönülür. */}
      <Button className="mt-8" size="lg" onPress={() => void auth.signinRedirect({ state: currentReturnPath() })}>
        {t('login.button')}
      </Button>
    </CenteredScreen>
  )
}
