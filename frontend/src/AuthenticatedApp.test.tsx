import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Me, UserStatus } from './api/me'
import { AuthenticatedApp } from './AuthenticatedApp'

function meWithStatus(status: UserStatus, displayName: string | null = 'Erdem Güral'): Me {
  return { id: '0193f1a2-0000-7000-8000-000000000001', email: 'erdem@example.test', displayName, role: 'USER', status }
}

function stubMeResponse(status: number, body: unknown) {
  const fetchMock = vi.fn(() => Promise.resolve(new Response(JSON.stringify(body), { status })))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

/** Uygulamayı verilen adreste açar. Yönlendirici tarayıcının adresini okur; jsdom'da da adres vardır. */
function renderAt(path: string, onSignOut = vi.fn()) {
  window.history.pushState({}, '', path)
  // Her test kendi önbelleğiyle başlar; bir testin yanıtı diğerine taşınmaz.
  render(
    <QueryClientProvider client={new QueryClient()}>
      <AuthenticatedApp accessToken="test-token" onSignOut={onSignOut} />
    </QueryClientProvider>,
  )
  return onSignOut
}

describe('AuthenticatedApp', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    window.history.pushState({}, '', '/')
  })

  it("/api/v1/me isteğine token'ı Authorization başlığında gönderir", async () => {
    const fetchMock = stubMeResponse(200, meWithStatus('ACTIVE'))

    renderAt('/')
    await screen.findByRole('navigation', { name: 'Ana menü' })

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/me', { headers: { Authorization: 'Bearer test-token' } })
  })

  it('aktif kullanıcıya menüyü ve arama sayfasını gösterir', async () => {
    stubMeResponse(200, meWithStatus('ACTIVE'))

    renderAt('/')

    const nav = await screen.findByRole('navigation', { name: 'Ana menü' })
    expect(nav).toContainElement(screen.getByRole('link', { name: 'Arama' }))
    expect(screen.getByRole('link', { name: 'Arama' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('heading', { level: 1, name: 'Haberlerde ara' })).toBeInTheDocument()
    expect(screen.getByText('Erdem Güral')).toBeInTheDocument()
  })

  it('görünen adı olmayan kullanıcının e-posta adresini gösterir', async () => {
    stubMeResponse(200, meWithStatus('ACTIVE', null))

    renderAt('/')

    expect(await screen.findByText('erdem@example.test')).toBeInTheDocument()
  })

  it('ilk odaklanılabilir öğe "İçeriğe geç" bağlantısıdır ve içeriğe götürür', async () => {
    stubMeResponse(200, meWithStatus('ACTIVE'))
    renderAt('/')
    await screen.findByRole('navigation', { name: 'Ana menü' })

    await userEvent.tab()

    const skipLink = screen.getByRole('link', { name: 'İçeriğe geç' })
    expect(skipLink).toHaveFocus()
    expect(skipLink).toHaveAttribute('href', '#main-content')
    expect(document.getElementById('main-content')).toBeInTheDocument()
  })

  it('tanımlı olmayan adreste bulunamadı sayfasını ve aramaya dönüş bağlantısını gösterir', async () => {
    stubMeResponse(200, meWithStatus('ACTIVE'))
    renderAt('/olmayan/sayfa')

    expect(await screen.findByRole('heading', { level: 1, name: 'Sayfa bulunamadı' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('link', { name: 'Aramaya dön' }))

    expect(screen.getByRole('heading', { level: 1, name: 'Haberlerde ara' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/')
  })

  it('menüdeki çıkış düğmesi çıkış işlemini başlatır', async () => {
    stubMeResponse(200, meWithStatus('ACTIVE'))
    const onSignOut = renderAt('/')

    await userEvent.click(await screen.findByRole('button', { name: 'Çıkış yap' }))

    expect(onSignOut).toHaveBeenCalledOnce()
  })

  it('hesabı aktif olmayan kullanıcıya menüyü değil hesap durumunu gösterir', async () => {
    stubMeResponse(200, meWithStatus('PENDING'))

    renderAt('/')

    expect(await screen.findByText('Hesabınız yönetici onayı bekliyor.')).toBeInTheDocument()
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument()
  })

  it('hesap bilgisi alınamazsa hata metnini ve çıkış düğmesini gösterir', async () => {
    stubMeResponse(500, { status: 500, title: 'Internal Server Error', code: 'INTERNAL_ERROR' })

    renderAt('/')

    expect(await screen.findByRole('alert')).toHaveTextContent('Hesap bilgileri alınamadı.')
    expect(screen.getByRole('button', { name: 'Çıkış yap' })).toBeInTheDocument()
  })
})
