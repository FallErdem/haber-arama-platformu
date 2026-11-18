import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { shouldRetry } from './api/client'
import type { Me, UserStatus } from './api/me'
import { AuthenticatedApp } from './AuthenticatedApp'

function meWithStatus(status: UserStatus, displayName: string | null = 'Erdem Güral'): Me {
  return { id: '0193f1a2-0000-7000-8000-000000000001', email: 'erdem@example.test', displayName, role: 'USER', status }
}

/**
 * API'yi taklit eder: `/me` verilen yanıtı döner. Arama sayfası açılınca istediği kaynak, kategori
 * ve haber listeleri boş döner; bu testler yalnızca uygulamanın çerçevesini sınar.
 */
function stubMeResponse(status: number, body: unknown) {
  const fetchMock = vi.fn((url: string) => {
    if (url === '/api/v1/me') return Promise.resolve(new Response(JSON.stringify(body), { status }))
    if (url.startsWith('/api/v1/articles')) {
      return Promise.resolve(
        Response.json({ items: [], page: 0, size: 20, totalElements: 0, totalPages: 0, totalRelation: 'eq' }),
      )
    }
    return Promise.resolve(Response.json({ items: [] }))
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

/** Uygulamayı verilen adreste açar. Yönlendirici tarayıcının adresini okur; jsdom'da da adres vardır. */
function renderAt(path: string, onSignOut = vi.fn(), onSessionExpired = vi.fn()) {
  window.history.pushState({}, '', path)
  // Her test kendi önbelleğiyle başlar; bir testin yanıtı diğerine taşınmaz. Yeniden deneme kuralı
  // uygulamadakiyle aynıdır (main.tsx).
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: shouldRetry } } })}>
      <AuthenticatedApp accessToken="test-token" onSignOut={onSignOut} onSessionExpired={onSessionExpired} />
    </QueryClientProvider>,
  )
  return onSignOut
}

const json = (status: number, body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status }))

describe('AuthenticatedApp', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    window.history.pushState({}, '', '/')
  })

  it("/api/v1/me isteğine token'ı Authorization başlığında gönderir", async () => {
    const fetchMock = stubMeResponse(200, meWithStatus('ACTIVE'))

    renderAt('/')
    await screen.findByRole('link', { name: 'Haber Arama Platformu' })

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/me', { headers: { Authorization: 'Bearer test-token' } })
  })

  it('aktif kullanıcıya üst çubuğu ve arama sayfasını gösterir; uygulamanın adı ana sayfaya götürür', async () => {
    stubMeResponse(200, meWithStatus('ACTIVE'))

    renderAt('/')

    const header = await screen.findByRole('banner')
    expect(within(header).getByRole('link', { name: 'Haber Arama Platformu' })).toHaveAttribute('href', '/')
    expect(within(header).getByText('Erdem Güral')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: 'Haberlerde ara' })).toBeInTheDocument()
  })

  it('görünen adı olmayan kullanıcının e-posta adresini gösterir', async () => {
    stubMeResponse(200, meWithStatus('ACTIVE', null))

    renderAt('/')

    expect(await screen.findByText('erdem@example.test')).toBeInTheDocument()
  })

  it('ilk odaklanılabilir öğe "İçeriğe geç" bağlantısıdır ve içeriğe götürür', async () => {
    stubMeResponse(200, meWithStatus('ACTIVE'))
    renderAt('/')
    await screen.findByRole('link', { name: 'Haber Arama Platformu' })

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

  it('hesabı aktif olmayan kullanıcıya uygulamayı değil hesap durumunu gösterir', async () => {
    stubMeResponse(200, meWithStatus('PENDING'))

    renderAt('/')

    expect(await screen.findByText('Hesabınız yönetici onayı bekliyor.')).toBeInTheDocument()
    expect(screen.queryByRole('banner')).not.toBeInTheDocument()
  })

  it('hesap bilgisi alınamazsa hata metnini ve çıkış düğmesini gösterir', async () => {
    stubMeResponse(500, { status: 500, title: 'Internal Server Error', code: 'INTERNAL_ERROR' })

    renderAt('/')

    expect(await screen.findByRole('alert')).toHaveTextContent('Hesap bilgileri alınamadı.')
    expect(screen.getByRole('button', { name: 'Çıkış yap' })).toBeInTheDocument()
  })

  it('bir istek 401 alırsa yeniden girişi bir kez başlatır', async () => {
    // Token yenilenemedi: sayfanın bütün istekleri (kaynaklar, kategoriler, arama) 401 alır.
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) =>
        url === '/api/v1/me' ? json(200, meWithStatus('ACTIVE')) : json(401, { code: 'UNAUTHENTICATED' }),
      ),
    )
    const onSessionExpired = vi.fn()

    renderAt('/', vi.fn(), onSessionExpired)

    await waitFor(() => expect(onSessionExpired).toHaveBeenCalled())
    expect(onSessionExpired).toHaveBeenCalledOnce()
  })

  it('oturum ortasında pasif yapılan kullanıcı hesap durumu ekranına geçer (ekran akışları 4.6)', async () => {
    // Kullanıcı açılışta aktiftir; yönetici onu pasif yapar ve sonraki istek 403 USER_PASSIVE alır.
    let status: UserStatus = 'ACTIVE'
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url === '/api/v1/me') return json(200, meWithStatus(status))
        if (url.startsWith('/api/v1/articles')) {
          status = 'PASSIVE'
          return json(403, { code: 'USER_PASSIVE' })
        }
        return json(200, { items: [] })
      }),
    )

    renderAt('/')

    expect(await screen.findByText('Hesabınız pasif duruma alınmış.')).toBeInTheDocument()
    expect(screen.queryByRole('banner')).not.toBeInTheDocument()
  })

  it('yetki eksikliğinden gelen 403 hesap bilgisini yeniden istemez', async () => {
    const fetchMock = vi.fn((url: string) => {
      if (url === '/api/v1/me') return json(200, meWithStatus('ACTIVE'))
      if (url.startsWith('/api/v1/articles')) return json(403, { code: 'FORBIDDEN' })
      return json(200, { items: [] })
    })
    vi.stubGlobal('fetch', fetchMock)

    renderAt('/')

    expect(await screen.findByText('Sonuçlar alınamadı.')).toBeInTheDocument()
    expect(fetchMock.mock.calls.filter(([url]) => url === '/api/v1/me')).toHaveLength(1)
  })
})
