import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { I18nProvider } from 'react-aria-components'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { SavedArticleItem, SavedArticlesResponse } from '../../api/savedArticles'
import { AccessTokenContext } from '../../auth/accessToken'
import { SavedArticlesPage } from './SavedArticlesPage'

const FIRST = '0193f1a2-0000-7000-8000-000000000001'
const SECOND = '0193f1a2-0000-7000-8000-000000000002'

function saved(articleId: string, title: string): SavedArticleItem {
  return {
    articleId,
    savedAt: '2026-11-18T10:00:00Z',
    hidden: false,
    article: {
      title,
      source: { code: 'TRT', name: 'TRT Haber' },
      publishedAt: '2026-11-18T08:12:00Z',
      image: null,
    },
  }
}

function hidden(articleId: string): SavedArticleItem {
  return { articleId, savedAt: '2026-11-18T10:00:00Z', hidden: true, article: null }
}

function page(items: SavedArticleItem[], overrides: Partial<SavedArticlesResponse> = {}): SavedArticlesResponse {
  return { items, page: 0, size: 20, totalElements: items.length, totalPages: items.length > 0 ? 1 : 0, ...overrides }
}

/**
 * API'yi taklit eder: liste isteği `list` fonksiyonunun yanıtını alır; kayıttan çıkarma 204 döner.
 * Bütün istekler `requests`'e yazılır.
 */
function stubApi(list: (page: string | null) => Response | SavedArticlesResponse) {
  const requests: { method: string; url: string }[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn((input: string, init?: RequestInit) => {
      const method = init?.method ?? 'GET'
      requests.push({ method, url: input })
      if (method !== 'GET') return Promise.resolve(new Response(null, { status: 204 }))
      const result = list(new URL(input, 'http://haber.localhost').searchParams.get('page'))
      return Promise.resolve(result instanceof Response ? result : Response.json(result))
    }),
  )
  return requests
}

/** Detay ve arama sayfalarının yerine geçer: bağlantının nereye götürdüğünü gösterir. */
function Destination() {
  const location = useLocation()
  return <p>Gidilen adres: {location.pathname}</p>
}

function renderAt(path: string) {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AccessTokenContext value="test-token">
        <I18nProvider locale="tr-TR">
          <MemoryRouter initialEntries={[path]}>
            <Routes>
              <Route path="/saved" element={<SavedArticlesPage />} />
              <Route path="*" element={<Destination />} />
            </Routes>
          </MemoryRouter>
        </I18nProvider>
      </AccessTokenContext>
    </QueryClientProvider>,
  )
}

describe('SavedArticlesPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("kaydedilen haberleri token'la ister ve haberin detayına bağlantı verir", async () => {
    const requests = stubApi(() => page([saved(FIRST, 'Deprem sonrası son durum')]))
    renderAt('/saved')

    await userEvent.click(await screen.findByRole('link', { name: 'Deprem sonrası son durum' }))

    expect(requests[0]).toEqual({ method: 'GET', url: '/api/v1/me/saved-articles?page=0' })
    expect(screen.getByText(`Gidilen adres: /articles/${FIRST}`)).toBeInTheDocument()
  })

  it("adresteki sayfa 1'den, API'deki 0'dan başlar", async () => {
    const pages: (string | null)[] = []
    stubApi((requested) => {
      pages.push(requested)
      return page([saved(FIRST, 'Haber')], { totalElements: 21, totalPages: 2 })
    })

    renderAt('/saved?page=2')
    await screen.findByRole('link', { name: 'Haber' })

    expect(pages).toEqual(['1'])
  })

  it('adresteki geçersiz sayfa numarası ilk sayfa sayılır', async () => {
    const pages: (string | null)[] = []
    stubApi((requested) => {
      pages.push(requested)
      return page([saved(FIRST, 'Haber')])
    })

    renderAt('/saved?page=abc')
    await screen.findByRole('link', { name: 'Haber' })

    expect(pages).toEqual(['0'])
  })

  it('gizlenen haberde bunu söyler; detaya bağlantı vermez, yalnızca kayıttan çıkarılabilir (FG-KO-03)', async () => {
    stubApi(() => page([hidden(FIRST)]))
    renderAt('/saved')

    const item = (await screen.findByText('Bu haber yönetici tarafından kaldırıldı.')).closest('article')!

    expect(within(item).queryByRole('link')).not.toBeInTheDocument()
    expect(within(item).getByRole('button', { name: /^Kaydet/ })).toHaveAttribute('aria-pressed', 'true')
  })

  it('yer imine basınca haber kayıttan çıkarılır ve liste yenilenince kaybolur', async () => {
    let items = [saved(FIRST, 'Birinci haber'), saved(SECOND, 'İkinci haber')]
    const requests = stubApi(() => page(items))
    renderAt('/saved')
    const bookmark = await screen.findByRole('button', { name: 'Kaydet: Birinci haber' })
    expect(bookmark).toHaveAttribute('aria-pressed', 'true')

    items = [saved(SECOND, 'İkinci haber')]
    await userEvent.click(bookmark)

    await waitFor(() => expect(screen.queryByText('Birinci haber')).not.toBeInTheDocument())
    expect(screen.getByRole('link', { name: 'İkinci haber' })).toBeInTheDocument()
    expect(requests).toContainEqual({ method: 'DELETE', url: `/api/v1/me/saved-articles/${FIRST}` })
  })

  it('kayıt yoksa bunu söyler ve aramaya bağlantı verir', async () => {
    stubApi(() => page([]))
    renderAt('/saved')

    expect(await screen.findByText('Henüz kaydettiğiniz bir haber yok.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Aramaya git' })).toHaveAttribute('href', '/')
  })

  it('sayfalama bağlantıları Kaydedilenlerin adresini taşır', async () => {
    stubApi(() => page([saved(FIRST, 'Haber')], { totalElements: 25, totalPages: 2 }))
    renderAt('/saved')

    const pages = await screen.findByRole('navigation', { name: 'Sayfalar' })

    expect(within(pages).getByRole('link', { name: /Sonraki/ })).toHaveAttribute('href', '/saved?page=2')
  })

  it('kayıt var ama bu sayfada yoksa ilk sayfaya dönüş bağlantısı gösterir', async () => {
    stubApi(() => page([], { totalElements: 3, totalPages: 1 }))
    renderAt('/saved?page=4')

    expect(await screen.findByText('Bu sayfada kayıt yok.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'İlk sayfaya dön' })).toHaveAttribute('href', '/saved')
  })

  it('liste alınamazsa hata mesajı gösterir ve yeniden denemeye izin verir', async () => {
    let fail = true
    stubApi(() => (fail ? new Response('{}', { status: 500 }) : page([saved(FIRST, 'Haber')])))
    renderAt('/saved')

    expect(await screen.findByRole('alert')).toHaveTextContent('Kaydedilen haberler alınamadı.')
    fail = false
    await userEvent.click(screen.getByRole('button', { name: 'Yeniden dene' }))

    expect(await screen.findByRole('link', { name: 'Haber' })).toBeInTheDocument()
  })
})
