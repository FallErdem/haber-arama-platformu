import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Me } from '../../api/me'
import { AccessTokenContext } from '../../auth/accessToken'
import { CurrentUserContext } from '../../auth/currentUser'
import { AdminLayout } from './AdminLayout'

const ADMIN: Me = {
  id: '0193f1a2-0000-7000-8000-0000000000a1',
  email: 'yonetici@example.test',
  displayName: 'Yönetici',
  role: 'ADMIN',
  status: 'ACTIVE',
}

/** Onay bekleyen kullanıcı sayısını soran isteğe `pending` ile yanıt verir. */
function stubPending(pending: number) {
  const fetchMock = vi.fn<(input: string) => Promise<Response>>(() =>
    Promise.resolve(Response.json({ items: [], page: 0, size: 1, totalElements: pending, totalPages: 1 })),
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function renderAt(path: string, currentUser: Me = ADMIN) {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AccessTokenContext value="test-token">
        <CurrentUserContext value={currentUser}>
          <MemoryRouter initialEntries={[path]}>
            <Routes>
              <Route path="/admin" element={<AdminLayout />}>
                <Route path="sources" element={<p>Kaynaklar ekranı</p>} />
              </Route>
            </Routes>
          </MemoryRouter>
        </CurrentUserContext>
      </AccessTokenContext>
    </QueryClientProvider>,
  )
}

describe('AdminLayout', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('yöneticiye yan menüyü ve seçili ekranı gösterir; bulunulan ekran menüde işaretlidir', () => {
    stubPending(0)
    renderAt('/admin/sources')

    const menu = screen.getByRole('navigation', { name: 'Yönetim menüsü' })
    const links = within(menu).getAllByRole('link')
    expect(links.map((link) => [link.textContent, link.getAttribute('href')])).toEqual([
      ['Pano', '/admin'],
      ['Kullanıcılar', '/admin/users'],
      ['Kaynaklar', '/admin/sources'],
      ['Toplama geçmişi', '/admin/ingestion-runs'],
      ['Gizlenen haberler', '/admin/hidden-articles'],
      ['Audit kayıtları', '/admin/audit-events'],
    ])
    expect(within(menu).getByRole('link', { name: 'Kaynaklar' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByText('Kaynaklar ekranı')).toBeInTheDocument()
  })

  it('onay bekleyen kullanıcı varsa Kullanıcılar bağlantısında sayısını gösterir ve ekran okuyucuya söyler', async () => {
    const fetchMock = stubPending(2)
    renderAt('/admin/sources')

    const menu = screen.getByRole('navigation', { name: 'Yönetim menüsü' })
    expect(await within(menu).findByRole('link', { name: 'Kullanıcılar, 2 onay bekleyen' })).toHaveAttribute(
      'href',
      '/admin/users',
    )
    const url = new URL(fetchMock.mock.calls[0][0], 'http://haber.localhost')
    expect(url.pathname).toBe('/api/v1/admin/users')
    expect(Object.fromEntries(url.searchParams)).toEqual({ status: 'PENDING', size: '1' })
  })

  it('onay bekleyen kullanıcı yoksa sayı göstermez', async () => {
    const fetchMock = stubPending(0)
    renderAt('/admin/sources')

    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    expect(screen.getByRole('link', { name: 'Kullanıcılar' })).toBeInTheDocument()
  })

  it('yönetici olmayan kullanıcıya menüyü ve ekranı göstermez; ekran çizilmediği için API isteği de gitmez', () => {
    const fetchMock = stubPending(0)
    renderAt('/admin/sources', { ...ADMIN, role: 'USER' })

    expect(screen.getByText('Bu sayfayı görüntüleme yetkiniz yok.')).toBeInTheDocument()
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument()
    expect(screen.queryByText('Kaynaklar ekranı')).not.toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
