import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { UserStatus } from '../../api/me'
import i18n from '../../i18n'
import { AccountStatus } from './AccountStatus'

type InactiveStatus = Exclude<UserStatus, 'ACTIVE'>

describe('AccountStatus', () => {
  afterEach(async () => {
    await i18n.changeLanguage('tr')
  })

  it.each<[InactiveStatus, string]>([
    ['PENDING', 'Hesabınız yönetici onayı bekliyor.'],
    ['PASSIVE', 'Hesabınız pasif duruma alınmış.'],
    ['REJECTED', 'Kayıt talebiniz reddedildi.'],
  ])('durumu %s olan kullanıcıya doğru metni gösterir', (status, expectedText) => {
    render(<AccountStatus status={status} onSignOut={vi.fn()} />)

    expect(screen.getByText(expectedText)).toBeInTheDocument()
  })

  it('çıkış düğmesine basılınca çıkış işlemini başlatır', async () => {
    const onSignOut = vi.fn()
    render(<AccountStatus status="PENDING" onSignOut={onSignOut} />)

    await userEvent.click(screen.getByRole('button', { name: 'Çıkış yap' }))

    expect(onSignOut).toHaveBeenCalledOnce()
  })

  it('dil değiştiğinde metinler bileşen değişmeden o dilde gösterilir', async () => {
    await i18n.changeLanguage('en')

    render(<AccountStatus status="PENDING" onSignOut={vi.fn()} />)

    expect(screen.getByText('Your account is waiting for administrator approval.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign out' })).toBeInTheDocument()
  })
})
