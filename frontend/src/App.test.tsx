import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { hasAuthParams, useAuth, type AuthContextProps } from 'react-oidc-context'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

// Testte gerçek Keycloak yoktur; giriş kütüphanesinin uygulamaya verdiği durum taklit edilir.
vi.mock('react-oidc-context', () => ({
  useAuth: vi.fn(),
  hasAuthParams: vi.fn(),
}))

function stubAuth(overrides: Partial<AuthContextProps> = {}) {
  const auth = {
    isLoading: false,
    isAuthenticated: false,
    user: undefined,
    error: undefined,
    // Keycloak'ta oturum yoksa kütüphane hata fırlatmaz, null döner.
    signinSilent: vi.fn(() => Promise.resolve(null)),
    signinRedirect: vi.fn(() => Promise.resolve()),
    signoutRedirect: vi.fn(() => Promise.resolve()),
    ...overrides,
  } as unknown as AuthContextProps
  vi.mocked(useAuth).mockReturnValue(auth)
  return auth
}

function renderApp() {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <App />
    </QueryClientProvider>,
  )
}

describe('App', () => {
  beforeEach(() => {
    vi.mocked(hasAuthParams).mockReturnValue(false)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  it('sayfa açılırken bir kez sessiz giriş dener', async () => {
    const auth = stubAuth()

    renderApp()

    await screen.findByRole('button', { name: 'Giriş yap' })
    expect(auth.signinSilent).toHaveBeenCalledOnce()
  })

  it('sessiz giriş sürerken giriş düğmesini göstermez', () => {
    // Hiç sonuçlanmayan bir deneme: Keycloak henüz yanıt vermedi.
    stubAuth({ signinSilent: vi.fn(() => new Promise<null>(() => {})) })

    renderApp()

    expect(screen.getByText('Yükleniyor…')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Giriş yap' })).not.toBeInTheDocument()
  })

  it('oturum yoksa giriş düğmesini gösterir ve basılınca Keycloak girişini başlatır', async () => {
    const auth = stubAuth()
    renderApp()

    await userEvent.click(await screen.findByRole('button', { name: 'Giriş yap' }))

    expect(auth.signinRedirect).toHaveBeenCalledOnce()
  })

  it('sessiz girişin başarısız olmasını hata olarak göstermez', async () => {
    stubAuth({ error: { source: 'signinSilent' } as AuthContextProps['error'] })

    renderApp()

    await screen.findByRole('button', { name: 'Giriş yap' })
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('kullanıcının başlattığı giriş başarısız olursa hata metnini gösterir', async () => {
    stubAuth({ error: { source: 'signinCallback' } as AuthContextProps['error'] })

    renderApp()

    expect(await screen.findByRole('alert')).toHaveTextContent('Giriş yapılamadı.')
  })

  it('girişten dönüş sayfasında sessiz giriş denemez', () => {
    vi.mocked(hasAuthParams).mockReturnValue(true)
    const auth = stubAuth()

    renderApp()

    expect(auth.signinSilent).not.toHaveBeenCalled()
  })

  it('giriş yapılmışsa sessiz giriş denemez ve hesap durumunu gösterir', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response(
            JSON.stringify({
              id: '1',
              email: 'erdem@example.test',
              displayName: 'Erdem',
              role: 'USER',
              status: 'PENDING',
            }),
            { status: 200 },
          ),
        ),
      ),
    )
    const auth = stubAuth({
      isAuthenticated: true,
      user: { access_token: 'test-token' } as AuthContextProps['user'],
    })

    renderApp()

    expect(await screen.findByText('Hesabınız yönetici onayı bekliyor.')).toBeInTheDocument()
    await waitFor(() => expect(auth.signinSilent).not.toHaveBeenCalled())
  })
})
