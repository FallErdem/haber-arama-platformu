import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { I18nProvider } from 'react-aria-components'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { AdminArticle } from '../../../api/adminArticles'
import { AccessTokenContext } from '../../../auth/accessToken'
import { HiddenArticlesPage } from './HiddenArticlesPage'

const HIDDEN: AdminArticle = {
  id: '0193f1a2-0000-7000-8000-0000000000a1',
  title: 'Yanıltıcı başlıklı haber',
  url: 'https://www.trthaber.com/haber/1',
  sourceCode: 'TRT',
  sourceName: 'TRT Haber',
  publishedAt: '2026-11-18T08:12:00Z',
  hidden: true,
  hiddenAt: '2026-11-20T09:30:00Z',
  hiddenReason: 'Başlık içerikle uyuşmuyor',
  hiddenBy: '0193f1a2-0000-7000-8000-0000000000b1',
  hiddenByEmail: 'yonetici@example.test',
}

interface Request {
  method: string
  url: URL
}

/** API'yi taklit eder; liste `items`'ı döner. İstekler kaydedilir. */
function stubApi(items: () => AdminArticle[] = () => [HIDDEN]) {
  const requests: Request[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn((input: string, init?: RequestInit) => {
      const url = new URL(input, 'http://haber.localhost')
      requests.push({ method: init?.method ?? 'GET', url })
      if (url.pathname === '/api/v1/admin/sources') {
        return Promise.resolve(Response.json({ items: [{ id: 's1', code: 'TRT', name: 'TRT Haber' }] }))
      }
      if (init?.method === 'POST') return Promise.resolve(Response.json({ ...HIDDEN, hidden: false }))
      const list = items()
      return Promise.resolve(
        Response.json({ items: list, page: 0, size: 20, totalElements: list.length, totalPages: 1 }),
      )
    }),
  )
  return {
    listQueries: () =>
      requests
        .filter((r) => r.method === 'GET' && r.url.pathname === '/api/v1/admin/articles')
        .map((r) => r.url.searchParams),
    posts: () => requests.filter((r) => r.method === 'POST').map((r) => r.url.pathname),
  }
}

function LocationProbe() {
  return <p data-testid="location">{useLocation().search}</p>
}

function renderAt(path: string) {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AccessTokenContext value="test-token">
        <I18nProvider locale="tr-TR">
          <MemoryRouter initialEntries={[path]}>
            <Routes>
              <Route
                path="/admin/hidden-articles"
                element={
                  <>
                    <HiddenArticlesPage />
                    <LocationProbe />
                  </>
                }
              />
            </Routes>
          </MemoryRouter>
        </I18nProvider>
      </AccessTokenContext>
    </QueryClientProvider>,
  )
}

describe('HiddenArticlesPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('gizlenen haberi kaynağı, gerekçesi, gizleyeni ve zamanıyla (Türkiye saati) gösterir (FG-YP-09)', async () => {
    stubApi()
    renderAt('/admin/hidden-articles')

    const list = within(await screen.findByRole('list'))
    // Detay sayfası gizli haberi göstermez; başlık haberi kaynağında açar.
    expect(list.getByRole('link', { name: /Yanıltıcı başlıklı haber/ })).toHaveAttribute(
      'href',
      'https://www.trthaber.com/haber/1',
    )
    expect(list.getByText('Başlık içerikle uyuşmuyor')).toBeInTheDocument()
    // 09:30 UTC, Türkiye'de 12:30'dur.
    expect(list.getByText('yonetici@example.test gizledi · 20 Kasım 2026 12:30')).toBeInTheDocument()
  })

  it("yalnızca gizli haberleri ister; adresteki filtreler API'ye gider, günler UTC anlarına çevrilir", async () => {
    const api = stubApi()

    renderAt('/admin/hidden-articles?source=TRT&from=2026-11-01&to=2026-11-05&page=2')

    await screen.findByRole('list')
    expect(Object.fromEntries(api.listQueries()[0])).toEqual({
      hidden: 'true',
      sources: 'TRT',
      from: '2026-10-31T21:00:00.000Z',
      to: '2026-11-05T20:59:59.999Z',
      page: '1',
    })
  })

  it('kaynak filtresi adrese yazılır ve ilk sayfaya dönülür', async () => {
    stubApi()
    renderAt('/admin/hidden-articles?page=3')
    await screen.findByRole('list')

    await userEvent.click(screen.getByRole('button', { name: /Kaynak$/ }))
    await userEvent.click(await screen.findByRole('option', { name: 'TRT Haber' }))

    expect(screen.getByTestId('location')).toHaveTextContent('?source=TRT')
  })

  it('"Gizlemeyi geri al" haberi yayına döndürür, bunu söyler ve listeyi yeniler', async () => {
    let hidden = [HIDDEN]
    const api = stubApi(() => hidden)
    renderAt('/admin/hidden-articles')

    const button = await screen.findByRole('button', { name: 'Gizlemeyi geri al: Yanıltıcı başlıklı haber' })
    hidden = []
    await userEvent.click(button)

    expect(await screen.findByRole('status')).toHaveTextContent('Haber yeniden yayında: Yanıltıcı başlıklı haber')
    expect(api.posts()).toEqual([`/api/v1/admin/articles/${HIDDEN.id}/unhide`])
    await waitFor(() => expect(screen.getByText('Gizlenmiş haber yok.')).toBeInTheDocument())
  })
})
