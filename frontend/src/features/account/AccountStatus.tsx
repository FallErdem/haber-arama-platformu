import { useTranslation } from 'react-i18next'
import type { UserStatus } from '../../api/me'
import { CenteredScreen } from '../../components/CenteredScreen'
import { Button } from '../../components/ui/button'

interface AccountStatusProps {
  status: Exclude<UserStatus, 'ACTIVE'>
  onSignOut: () => void
}

/**
 * Hesabı aktif olmayan kullanıcıya durumunu gösterir (onay bekliyor, reddedildi, pasif). Durum her
 * zaman API'den gelir; arayüz kendi başına karar vermez.
 */
export function AccountStatus({ status, onSignOut }: AccountStatusProps) {
  const { t } = useTranslation()

  return (
    <CenteredScreen>
      <h1 className="text-3xl font-semibold tracking-tight">{t('app.brand')}</h1>
      <p className="mt-4">{t(`account.status.${status}`)}</p>
      <Button variant="outline" className="mt-8" onPress={onSignOut}>
        {t('logout.button')}
      </Button>
    </CenteredScreen>
  )
}
