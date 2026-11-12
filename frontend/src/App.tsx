import { useTranslation } from 'react-i18next'
import { useAuth } from 'react-oidc-context'
import { useSilentLogin } from './auth/useSilentLogin'
import { AccountStatus } from './features/account/AccountStatus'

export default function App() {
  const auth = useAuth()
  const { t } = useTranslation()
  const isSilentLoginDone = useSilentLogin(auth)

  if (auth.isLoading || !isSilentLoginDone) {
    return (
      <main>
        <p>{t('common.loading')}</p>
      </main>
    )
  }

  if (auth.isAuthenticated && auth.user) {
    return <AccountStatus accessToken={auth.user.access_token} onSignOut={() => void auth.signoutRedirect()} />
  }

  // Sessiz giriş denemesinin başarısız olması olağandır (kullanıcı henüz giriş
  // yapmamıştır); yalnızca kullanıcının başlattığı girişin hatası gösterilir.
  const hasLoginFailed = auth.error !== undefined && auth.error.source !== 'signinSilent'

  return (
    <main>
      <h1>{t('app.title')}</h1>
      {hasLoginFailed && <p role="alert">{t('login.failed')}</p>}
      <button type="button" onClick={() => void auth.signinRedirect()}>
        {t('login.button')}
      </button>
    </main>
  )
}
