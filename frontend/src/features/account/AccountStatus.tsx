import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { fetchMe } from '../../api/me'

interface AccountStatusProps {
  accessToken: string
  onSignOut: () => void
}

/**
 * Giriş yapmış kullanıcıya hesabının durumunu gösterir. Durum her zaman
 * API'den gelir; arayüz kendi başına karar vermez.
 */
export function AccountStatus({ accessToken, onSignOut }: AccountStatusProps) {
  const { t } = useTranslation()
  const me = useQuery({
    queryKey: ['me'],
    queryFn: () => fetchMe(accessToken),
    retry: false,
  })

  if (me.isPending) {
    return (
      <main>
        <p>{t('common.loading')}</p>
      </main>
    )
  }

  return (
    <main>
      <h1>{t('app.title')}</h1>
      {me.isError ? (
        <p role="alert">{t('account.loadFailed')}</p>
      ) : (
        <p>{t(`account.status.${me.data.status}`, { name: me.data.displayName ?? me.data.email })}</p>
      )}
      <button type="button" onClick={onSignOut}>
        {t('logout.button')}
      </button>
    </main>
  )
}
