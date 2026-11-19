import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { I18nProvider } from 'react-aria-components'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { AdminUser, AdminUsersResponse } from '../../../api/adminUsers'
import type { Me } from '../../../api/me'
import { AccessTokenContext } from '../../../auth/accessToken'
import { CurrentUserContext } from '../../../auth/currentUser'
import { AdminUsersPage } from './AdminUsersPage'

const ADMIN: Me = {
  id: '0193f1a2-0000-7000-8000-0000000000a1',
  email: 'yonetici@example.test',
  displayName: 'Yönetici',
  role: 'ADMIN',
  status: 'ACTIVE',
}

function user(overrides: Partial<AdminUser>): AdminUser {
  return {
    id: '0193f1a2-0000-7000-8000-000000000001',
    email: 'ahmet@example.test',
    displayName: 'Ahmet Şahin',
    role: 'USER',
    status: 'PENDING',
    createdAt: '2026-11-18T08:12:00Z',
    version: 0,
    ...overrides,
  }
}

const PENDING = user({})
const ACTIVE = user({
  id: '0193f1a2-0000-7000-8000-000000000002',
  email: 'ayse@example.test',
  displayName: 'Ayşe Yılmaz',
  status: 'ACTIVE',
  version: 3,
})

function page(items: AdminUser[]): AdminUsersResponse {
  return { items, page: 0, size: 20, totalElements: items.length, totalPages: items.length > 0 ? 1 : 0 }
}

interface Request {
  method: string
  url: string
  body: unknown
}

/**
 * API'yi taklit eder: liste istekleri `list`'in, işlem istekleri (`POST`, `PATCH`) `action`'ın yanıtını
 * alır. Bütün istekler gövdeleriyle `requests`'e yazılır.
 */
function stubApi(
  list: () => AdminUsersResponse = () => page([PENDING, ACTIVE]),
  action: () => Response = () => Response.json(ACTIVE),
) {
  const requests: Request[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      const method = init?.method ?? 'GET'
      requests.push({ method, url, body: init?.body ? JSON.parse(init.body as string) : undefined })
      return Promise.resolve(method === 'GET' ? Response.json(list()) : action())
    }),
  )
  return {
    requests,
    lists: () => requests.filter((request) => request.method === 'GET'),
    actions: () => requests.filter((request) => request.method !== 'GET'),
  }
}

/** Adres çubuğunun şu anki sorgu kısmını gösterir; filtrelerin adrese yazıldığını sınamak için. */
function LocationProbe() {
  return <p data-testid="location">{useLocation().search}</p>
}

function renderAt(path: string, currentUser: Me = ADMIN) {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AccessTokenContext value="test-token">
        <CurrentUserContext value={currentUser}>
          <I18nProvider locale="tr-TR">
            <MemoryRouter initialEntries={[path]}>
              <Routes>
                <Route
                  path="/admin/users"
                  element={
                    <>
                      <AdminUsersPage />
                      <LocationProbe />
                    </>
                  }
                />
              </Routes>
            </MemoryRouter>
          </I18nProvider>
        </CurrentUserContext>
      </AccessTokenContext>
    </QueryClientProvider>,
  )
}

/** Kullanıcının satırı: adının bulunduğu liste öğesi. */
async function rowOf(name: string) {
  return (await screen.findByText(name)).closest('li')!
}

describe('AdminUsersPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("adresteki filtrelerle listeyi ister; sayfa API'de 0'dan başlar", async () => {
    const api = stubApi()

    renderAt('/admin/users?status=PENDING&q=ahmet&page=2')

    await screen.findByText('Ahmet Şahin')
    const url = new URL(api.lists()[0].url, 'http://haber.localhost')
    expect(url.pathname).toBe('/api/v1/admin/users')
    expect(Object.fromEntries(url.searchParams)).toEqual({ status: 'PENDING', q: 'ahmet', page: '1' })
  })

  it('kullanıcının adını, e-postasını ve kayıt zamanını Türkiye saatiyle gösterir', async () => {
    stubApi()
    renderAt('/admin/users')

    const row = await rowOf('Ahmet Şahin')

    expect(within(row).getByText('ahmet@example.test')).toBeInTheDocument()
    // 08:12 UTC, Türkiye'de 11:12'dir.
    expect(within(row).getByText('Kayıt: 18 Kasım 2026 11:12')).toBeInTheDocument()
    expect(within(row).getByText('Onay bekliyor')).toBeInTheDocument()
  })

  it('durum filtresi adrese yazılır ve ilk sayfaya dönülür', async () => {
    stubApi()
    renderAt('/admin/users?page=3')
    await screen.findByText('Ahmet Şahin')

    // Seçim kutusunun adı seçili değer ve etiketten oluşur ("Tüm durumlar Durum").
    await userEvent.click(screen.getByRole('button', { name: /Durum$/ }))
    await userEvent.click(await screen.findByRole('option', { name: 'Onay bekliyor' }))

    expect(screen.getByTestId('location')).toHaveTextContent('?status=PENDING')
  })

  it('onay bekleyen kullanıcı onaylanır ve liste yeniden istenir', async () => {
    const api = stubApi()
    renderAt('/admin/users')
    const row = await rowOf('Ahmet Şahin')

    await userEvent.click(within(row).getByRole('button', { name: 'Onayla' }))

    await waitFor(() => expect(api.lists()).toHaveLength(2))
    expect(api.actions()).toEqual([
      { method: 'POST', url: `/api/v1/admin/users/${PENDING.id}/approve`, body: undefined },
    ])
  })

  it('reddetme onay penceresi ister; Vazgeç hiçbir şey göndermez, onaylayınca reddedilir', async () => {
    const api = stubApi()
    renderAt('/admin/users')
    const row = await rowOf('Ahmet Şahin')

    await userEvent.click(within(row).getByRole('button', { name: 'Reddet' }))
    const dialog = await screen.findByRole('dialog', { name: 'Kayıt talebini reddet' })
    expect(within(dialog).getByText(/Ahmet Şahin kullanıcısının kayıt talebi reddedilecek/)).toBeInTheDocument()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Vazgeç' }))

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(api.actions()).toEqual([])

    await userEvent.click(within(row).getByRole('button', { name: 'Reddet' }))
    await userEvent.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Reddet' }))

    await waitFor(() =>
      expect(api.actions()).toEqual([
        { method: 'POST', url: `/api/v1/admin/users/${PENDING.id}/reject`, body: undefined },
      ]),
    )
  })

  it('rol değişikliği kaydın sürümüyle birlikte gönderilir', async () => {
    const api = stubApi()
    renderAt('/admin/users')
    await screen.findByText('Ayşe Yılmaz')

    await userEvent.click(screen.getByRole('button', { name: /Rol: Ayşe Yılmaz$/ }))
    await userEvent.click(await screen.findByRole('option', { name: 'Yönetici' }))

    await waitFor(() =>
      expect(api.actions()).toEqual([
        { method: 'PATCH', url: `/api/v1/admin/users/${ACTIVE.id}`, body: { role: 'ADMIN', version: 3 } },
      ]),
    )
  })

  it("son aktif yöneticiyi kaldıracak değişiklikte API'nin hatasını açıklayan mesaj gösterir", async () => {
    stubApi(undefined, () => new Response(JSON.stringify({ code: 'LAST_ACTIVE_ADMIN' }), { status: 409 }))
    renderAt('/admin/users')
    await screen.findByText('Ayşe Yılmaz')

    await userEvent.click(screen.getByRole('button', { name: /Durum: Ayşe Yılmaz$/ }))
    await userEvent.click(await screen.findByRole('option', { name: 'Pasif' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Sistemde en az bir aktif yönetici bulunmalıdır.')
  })

  it('kayıt bu arada değiştiyse bunu söyler ve listeyi yeniden ister', async () => {
    const api = stubApi(undefined, () => new Response(JSON.stringify({ code: 'VERSION_CONFLICT' }), { status: 409 }))
    renderAt('/admin/users')
    await screen.findByText('Ayşe Yılmaz')

    await userEvent.click(screen.getByRole('button', { name: /Rol: Ayşe Yılmaz$/ }))
    await userEvent.click(await screen.findByRole('option', { name: 'Yönetici' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('başka bir yönetici tarafından değiştirildi')
    await waitFor(() => expect(api.lists()).toHaveLength(2))
  })

  it('filtrelere uyan kullanıcı yoksa bunu söyler', async () => {
    stubApi(() => page([]))
    renderAt('/admin/users?q=yok')

    expect(await screen.findByText('Bu ölçütlere uyan kullanıcı yok.')).toBeInTheDocument()
  })

  it("yönetici olmayan kullanıcıya içerik göstermez ve API'ye sormaz", () => {
    const api = stubApi()

    renderAt('/admin/users', { ...ADMIN, role: 'USER' })

    expect(screen.getByText('Bu sayfayı görüntüleme yetkiniz yok.')).toBeInTheDocument()
    expect(api.requests).toEqual([])
  })
})
