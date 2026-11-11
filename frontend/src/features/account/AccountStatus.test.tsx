import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Me, UserStatus } from '../../api/me'
import i18n from '../../i18n'
import { AccountStatus } from './AccountStatus'

function meWithStatus(status: UserStatus, displayName: string | null = 'Erdem Güral'): Me {
  return { id: '0193f1a2-0000-7000-8000-000000000001', email: 'erdem@example.test', displayName, role: 'USER', status }
}

function stubMeResponse(status: number, body: unknown) {
  const fetchMock = vi.fn(() => Promise.resolve(new Response(JSON.stringify(body), { status })))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function renderAccountStatus(onSignOut = vi.fn()) {
  // Her test kendi önbelleğiyle başlar; bir testin yanıtı diğerine taşınmaz.
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <AccountStatus accessToken="test-token" onSignOut={onSignOut} />
    </QueryClientProvider>,
  )
  return onSignOut
}

describe('AccountStatus', () => {
  afterEach(async () => {
    vi.unstubAllGlobals()
    await i18n.changeLanguage('tr')
  })

  it.each<[UserStatus, string]>([
    ['PENDING', 'Hesabınız yönetici onayı bekliyor.'],
    ['ACTIVE', 'Hoş geldiniz, Erdem Güral.'],
    ['PASSIVE', 'Hesabınız pasif duruma alınmış.'],
    ['REJECTED', 'Kayıt talebiniz reddedildi.'],
  ])('durumu %s olan kullanıcıya doğru metni gösterir', async (status, expectedText) => {
    stubMeResponse(200, meWithStatus(status))

    renderAccountStatus()

    expect(await screen.findByText(expectedText)).toBeInTheDocument()
  })

  it('görünen ad yoksa e-posta adresiyle karşılar', async () => {
    stubMeResponse(200, meWithStatus('ACTIVE', null))

    renderAccountStatus()

    expect(await screen.findByText('Hoş geldiniz, erdem@example.test.')).toBeInTheDocument()
  })

  it("/api/v1/me isteğine token'ı Authorization başlığında gönderir", async () => {
    const fetchMock = stubMeResponse(200, meWithStatus('ACTIVE'))

    renderAccountStatus()
    await screen.findByText('Hoş geldiniz, Erdem Güral.')

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/me', { headers: { Authorization: 'Bearer test-token' } })
  })

  it('API hata döndüğünde hata metnini gösterir', async () => {
    stubMeResponse(500, { status: 500, title: 'Internal Server Error', code: 'INTERNAL_ERROR' })

    renderAccountStatus()

    expect(await screen.findByRole('alert')).toHaveTextContent('Hesap bilgileri alınamadı.')
  })

  it('çıkış düğmesine basılınca çıkış işlemini başlatır', async () => {
    stubMeResponse(200, meWithStatus('ACTIVE'))
    const onSignOut = renderAccountStatus()

    await userEvent.click(await screen.findByRole('button', { name: 'Çıkış yap' }))

    expect(onSignOut).toHaveBeenCalledOnce()
  })

  it('dil değiştiğinde metinler bileşen değişmeden o dilde gösterilir', async () => {
    await i18n.changeLanguage('en')
    stubMeResponse(200, meWithStatus('PENDING'))

    renderAccountStatus()

    expect(await screen.findByText('Your account is waiting for administrator approval.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign out' })).toBeInTheDocument()
  })
})
