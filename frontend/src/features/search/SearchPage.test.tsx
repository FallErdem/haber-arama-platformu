import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { I18nProvider } from 'react-aria-components'
import { BrowserRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ArticleSearchItem, ArticleSearchResponse } from '../../api/articles'
import { AccessTokenContext } from '../../auth/accessToken'
import { SearchPage } from './SearchPage'

const SOURCES = [
  { code: 'NTV', name: 'NTV', language: 'tr' },
  { code: 'TRT', name: 'TRT Haber', language: 'tr' },
]
const CATEGORIES = [
  { code: 'GENERAL', kind: 'TOPIC', sortOrder: 10 },
  { code: 'WORLD', kind: 'TOPIC', sortOrder: 20 },
  { code: 'BREAKING', kind: 'TEMPORAL', sortOrder: 90 },
]

function article(overrides: Partial<ArticleSearchItem> = {}): ArticleSearchItem {
  return {
    id: '0193f1a2-0000-7000-8000-000000000001',
    title: 'Deprem sonrası son durum',
    summary: 'Bölgede çalışmalar sürüyor.',
    source: { code: 'TRT', name: 'TRT Haber' },
    language: 'tr',
    itemType: 'ARTICLE',
    categories: ['GENERAL'],
    publishedAt: '2026-11-05T08:12:00Z',
    url: 'https://www.trthaber.com/haber/1',
    image: null,
    otherSourcesCount: 0,
    saved: false,
    ...overrides,
  }
}

function page(items: ArticleSearchItem[], overrides: Partial<ArticleSearchResponse> = {}): ArticleSearchResponse {
  return { items, page: 0, size: 20, totalElements: items.length, totalPages: 1, totalRelation: 'eq', ...overrides }
}

/**
 * API'yi taklit eder: kaynak ve kategori listeleri sabit, arama yanıtı testin verdiği fonksiyondan.
 * Kaydetme istekleri (`PUT`/`DELETE`) `saving` yanıtını alır (varsayılan 204) ve `savings`'e yazılır.
 */
function stubApi(
  search: (params: URLSearchParams) => Response | ArticleSearchResponse,
  saving: () => Response = () => new Response(null, { status: 204 }),
) {
  const searches: URLSearchParams[] = []
  const savings: { method: string | undefined; path: string }[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn((input: string, init?: RequestInit) => {
      const url = new URL(input, 'http://haber.localhost')
      if (url.pathname === '/api/v1/sources') return Promise.resolve(Response.json({ items: SOURCES }))
      if (url.pathname === '/api/v1/categories') return Promise.resolve(Response.json({ items: CATEGORIES }))
      if (url.pathname.startsWith('/api/v1/me/saved-articles/')) {
        savings.push({ method: init?.method, path: url.pathname })
        return Promise.resolve(saving())
      }
      searches.push(url.searchParams)
      const result = search(url.searchParams)
      return Promise.resolve(result instanceof Response ? result : Response.json(result))
    }),
  )
  return { searches, savings, lastSearch: () => searches[searches.length - 1] }
}

function renderAt(path: string) {
  window.history.pushState({}, '', path)
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AccessTokenContext value="test-token">
        <I18nProvider locale="tr-TR">
          <BrowserRouter>
            <SearchPage />
          </BrowserRouter>
        </I18nProvider>
      </AccessTokenContext>
    </QueryClientProvider>,
  )
}

const search = () => new URLSearchParams(window.location.search)

describe('SearchPage', () => {
  beforeEach(() => {
    vi.stubGlobal('scrollTo', vi.fn())
  })

  afterEach(() => {
    // Test ortada düşse de sahte saat sonraki teste geçmez.
    vi.useRealTimers()
    vi.unstubAllGlobals()
    window.history.pushState({}, '', '/')
  })

  it('arama ifadesi yokken en yeni haberleri ister ve listeler', async () => {
    const api = stubApi(() => page([article()]))

    renderAt('/')

    expect(await screen.findByRole('link', { name: 'Deprem sonrası son durum' })).toHaveAttribute(
      'href',
      '/articles/0193f1a2-0000-7000-8000-000000000001',
    )
    expect(Object.fromEntries(api.lastSearch())).toEqual({ page: '0', size: '20' })
    const result = screen.getByRole('article')
    expect(within(result).getByText('TRT Haber')).toBeInTheDocument()
    expect(within(result).getByText('Bölgede çalışmalar sürüyor.')).toBeInTheDocument()
    // İfade yokken sıralama seçeneği gösterilmez; sonuçlar yalnızca tarihe göre sıralanır.
    expect(screen.queryByRole('button', { name: /Sıralama/ })).not.toBeInTheDocument()
  })

  it("yazılan ifade aranınca adrese yazılır ve API'ye gönderilir", async () => {
    const api = stubApi(() => page([]))
    renderAt('/')

    await userEvent.type(await screen.findByRole('searchbox', { name: 'Arama ifadesi' }), 'deprem')
    await userEvent.click(screen.getByRole('button', { name: 'Ara' }))

    await waitFor(() => expect(search().get('q')).toBe('deprem'))
    await waitFor(() => expect(api.lastSearch().get('q')).toBe('deprem'))
  })

  it('adresteki aramayı açar; adres paylaşılınca aynı sonuçlar gelir', async () => {
    const api = stubApi(() => page([]))

    renderAt('/?q=deprem&sources=TRT&page=2')

    expect(await screen.findByRole('searchbox', { name: 'Arama ifadesi' })).toHaveValue('deprem')
    await waitFor(() =>
      expect(Object.fromEntries(api.lastSearch())).toEqual({ q: 'deprem', sources: 'TRT', page: '1', size: '20' }),
    )
  })

  it('eşleşen kelimeleri vurgular; vurgudaki metni HTML olarak işlemez', async () => {
    stubApi(() =>
      page([
        article({
          highlights: {
            title: ['<mark>Deprem</mark> sonrası son durum'],
            summary: ['&lt;b&gt;Bölgede&lt;/b&gt; <mark>deprem</mark> çalışmaları'],
          },
        }),
      ]),
    )

    renderAt('/?q=deprem')

    const link = await screen.findByRole('link', { name: 'Deprem sonrası son durum' })
    expect(within(link).getByText('Deprem').tagName).toBe('MARK')
    expect(screen.getByText('<b>Bölgede</b>', { exact: false })).toBeInTheDocument()
    expect(document.querySelector('b')).toBeNull()
  })

  it('görseli olan haberde imzalı adresi, olmayanda yer tutucuyu gösterir', async () => {
    stubApi(() =>
      page([
        article({ image: { url: '/api/v1/media/m1?exp=1&sig=s', width: 1200, height: 675 } }),
        article({ id: '0193f1a2-0000-7000-8000-000000000002', title: 'Görselsiz haber' }),
      ]),
    )

    renderAt('/')

    await screen.findByText('Görselsiz haber')
    const images = document.querySelectorAll('img')
    expect(images).toHaveLength(1)
    expect(images[0]).toHaveAttribute('src', '/api/v1/media/m1?exp=1&sig=s')
    expect(images[0]).toHaveAttribute('alt', '')
  })

  it('kaynak seçilince adrese yazılır ve ilk sayfaya dönülür', async () => {
    stubApi(() => page([article()], { totalElements: 60, totalPages: 3 }))
    renderAt('/?q=deprem&page=3')

    await userEvent.click(await screen.findByRole('button', { name: /Kaynak/ }))
    await userEvent.click(await screen.findByRole('option', { name: 'TRT Haber' }))

    await waitFor(() => expect(search().get('sources')).toBe('TRT'))
    expect(search().get('page')).toBeNull()
  })

  it('kategori listesinde yalnızca konu kategorileri dil dosyasındaki adlarıyla yer alır', async () => {
    stubApi(() => page([]))
    renderAt('/')

    await userEvent.click(await screen.findByRole('button', { name: /Kategori/ }))

    const options = (await screen.findAllByRole('option')).map((option) => option.textContent)
    expect(options).toEqual(['Gündem', 'Dünya'])
  })

  it('Son Dakika düğmesi BREAKING kategorisini ekler ve kaldırır', async () => {
    stubApi(() => page([]))
    renderAt('/?categories=WORLD')

    const toggle = await screen.findByRole('button', { name: 'Son Dakika' })
    await userEvent.click(toggle)
    await waitFor(() => expect(search().get('categories')).toBe('WORLD,BREAKING'))
    expect(toggle).toHaveAttribute('aria-pressed', 'true')

    await userEvent.click(toggle)
    await waitFor(() => expect(search().get('categories')).toBe('WORLD'))
  })

  it('dil seçilince adrese yazılır; "Tüm diller" filtreyi kaldırır', async () => {
    stubApi(() => page([]))
    renderAt('/')

    await userEvent.click(await screen.findByRole('button', { name: /Dil/ }))
    await userEvent.click(await screen.findByRole('option', { name: 'İngilizce' }))
    await waitFor(() => expect(search().get('language')).toBe('en'))

    await userEvent.click(screen.getByRole('button', { name: /İngilizce/ }))
    await userEvent.click(await screen.findByRole('option', { name: 'Tüm diller' }))
    await waitFor(() => expect(search().has('language')).toBe(false))
  })

  it('takvimde iki gün seçilince tarih aralığı adrese yazılır', async () => {
    // Gelecekteki günler seçilemez; testin sonucu çalıştığı güne bağlı olmasın diye bugün sabitlenir.
    // Yalnızca Date sahtelenir; zamanlayıcılar gerçek kalır.
    vi.useFakeTimers({ toFake: ['Date'], now: new Date('2026-11-18T12:00:00Z') })
    stubApi(() => page([]))
    renderAt('/')

    await userEvent.click(await screen.findByRole('button', { name: 'Tarih' }))
    const calendar = await screen.findByRole('dialog', { name: 'Tarih' })
    const day = (number: string) =>
      within(calendar)
        .getAllByRole('button')
        .find((cell) => cell.textContent === number)!
    await userEvent.click(day('3'))
    await userEvent.click(day('9'))

    await waitFor(() => expect(search().get('from')).toBe('2026-11-03'))
    expect(search().get('to')).toBe('2026-11-09')
  })

  it('"Filtreleri temizle" bütün filtreleri kaldırır, arama ifadesini korur', async () => {
    stubApi(() => page([article()]))
    renderAt('/?q=deprem&sources=TRT&language=tr&from=2026-11-01&to=2026-11-05')

    await userEvent.click(await screen.findByRole('button', { name: 'Filtreleri temizle' }))

    await waitFor(() => expect(window.location.search).toBe('?q=deprem'))
  })

  it('arama ifadesi varken sıralama seçilebilir', async () => {
    stubApi(() => page([article()]))
    renderAt('/?q=deprem')

    await userEvent.click(await screen.findByRole('button', { name: /İlgililik/ }))
    await userEvent.click(await screen.findByRole('option', { name: 'En yeni' }))

    await waitFor(() => expect(search().get('sort')).toBe('newest'))
  })

  it('sonuç sayısını gösterir; 10.000\'den fazlasını "10.000+" olarak yazar', async () => {
    stubApi((params) =>
      params.get('q') === 'çok'
        ? page([article()], { totalElements: 10000, totalPages: 500, totalRelation: 'gte' })
        : page([article()], { totalElements: 1284, totalPages: 65 }),
    )

    renderAt('/?q=deprem')
    expect(await screen.findByText('1.284 sonuç')).toBeInTheDocument()

    await userEvent.clear(screen.getByRole('searchbox'))
    await userEvent.type(screen.getByRole('searchbox'), 'çok{Enter}')
    expect(await screen.findByText('10.000+ sonuç')).toBeInTheDocument()
  })

  it('sonuç yoksa mesaj ve filtreleri temizleme seçeneği gösterir', async () => {
    stubApi(() => page([]))

    renderAt('/?q=zzz&sources=TRT')

    expect(await screen.findByText('Aramanızla eşleşen haber bulunamadı.')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Filtreleri temizle' }).length).toBeGreaterThan(0)
  })

  it('sayfalama bağlantıları sayfanın adresini taşır; ilk sayfada "Önceki" yoktur', async () => {
    stubApi(() => page([article()], { totalElements: 45, totalPages: 3 }))

    renderAt('/?q=deprem')

    const pages = await screen.findByRole('navigation', { name: 'Sayfalar' })
    expect(within(pages).getByText('Sayfa 1 / 3')).toBeInTheDocument()
    expect(within(pages).queryByRole('link', { name: /Önceki/ })).not.toBeInTheDocument()
    expect(within(pages).getByRole('link', { name: /Sonraki/ })).toHaveAttribute('href', '/?q=deprem&page=2')
  })

  it('sayfa numaralarını gösterir; bulunulan sayfa bağlantı değildir ve öyle işaretlenir', async () => {
    stubApi(() => page([article()], { totalElements: 3000, totalPages: 150 }))

    renderAt('/?q=deprem&page=2')

    const pages = await screen.findByRole('navigation', { name: 'Sayfalar' })
    const numbers = within(pages)
      .getAllByRole('link', { name: /^Sayfa \d+$/ })
      .map((link) => [link.textContent, link.getAttribute('href')])
    expect(numbers).toEqual([
      ['1', '/?q=deprem'],
      ['3', '/?q=deprem&page=3'],
      ['4', '/?q=deprem&page=4'],
      ['5', '/?q=deprem&page=5'],
      ['150', '/?q=deprem&page=150'],
    ])
    const current = within(pages).getByText('2')
    expect(current).toHaveAttribute('aria-current', 'page')
    expect(current.tagName).not.toBe('A')
  })

  it('listenin üstünde de önceki ve sonraki sayfa bağlantısı vardır', async () => {
    stubApi(() => page([article()], { totalElements: 3000, totalPages: 150 }))

    renderAt('/?q=deprem&page=2')

    const quick = await screen.findByRole('navigation', { name: 'Hızlı sayfa geçişi' })
    expect(within(quick).getByRole('link', { name: 'Önceki' })).toHaveAttribute('href', '/?q=deprem')
    expect(within(quick).getByRole('link', { name: 'Sonraki' })).toHaveAttribute('href', '/?q=deprem&page=3')
    expect(within(quick).getByText('Sayfa 2 / 150')).toBeInTheDocument()
  })

  it("10.000 sonuç sınırında son sayfa 500'dür ve aramayı daraltma önerisi gösterilir", async () => {
    stubApi(() => page([article()], { totalElements: 10000, totalPages: 1200, totalRelation: 'gte' }))

    renderAt('/?q=a&page=500')

    const pages = await screen.findByRole('navigation', { name: 'Sayfalar' })
    expect(within(pages).getByText('Sayfa 500 / 500')).toBeInTheDocument()
    expect(within(pages).queryByRole('link', { name: /Sonraki/ })).not.toBeInTheDocument()
    expect(within(pages).getByText(/aramanızı daraltın/)).toBeInTheDocument()
  })

  it('var olmayan bir sayfada ilk sayfaya dönüş bağlantısı gösterir', async () => {
    stubApi(() => page([], { totalElements: 3, totalPages: 1 }))

    renderAt('/?q=deprem&page=7')

    expect(await screen.findByText('Bu sayfada sonuç yok.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'İlk sayfaya dön' })).toHaveAttribute('href', '/?q=deprem')
  })

  it('sonuçlar alınamazsa hata mesajı gösterir ve yeniden denemeye izin verir', async () => {
    let fail = true
    stubApi(() => (fail ? new Response('{}', { status: 500 }) : page([article()])))
    renderAt('/?q=deprem')

    expect(await screen.findByRole('alert')).toHaveTextContent('Sonuçlar alınamadı.')
    fail = false
    await userEvent.click(screen.getByRole('button', { name: 'Yeniden dene' }))

    expect(await screen.findByRole('link', { name: 'Deprem sonrası son durum' })).toBeInTheDocument()
  })

  it('sonuçtaki yer imi haberi kaydeder ve dolu görünür; arama yeniden istenmez', async () => {
    const api = stubApi(() => page([article()]))
    renderAt('/?q=deprem')
    const bookmark = await screen.findByRole('button', { name: 'Kaydet: Deprem sonrası son durum' })
    expect(bookmark).toHaveAttribute('aria-pressed', 'false')

    await userEvent.click(bookmark)

    await waitFor(() => expect(bookmark).toHaveAttribute('aria-pressed', 'true'))
    expect(api.savings).toEqual([
      { method: 'PUT', path: '/api/v1/me/saved-articles/0193f1a2-0000-7000-8000-000000000001' },
    ])
    expect(api.searches).toHaveLength(1)
  })

  it('kaydedilmiş haberin yer imi basılıdır; basınca haber kayıttan çıkarılır', async () => {
    const api = stubApi(() => page([article({ saved: true })]))
    renderAt('/?q=deprem')
    const bookmark = await screen.findByRole('button', { name: 'Kaydet: Deprem sonrası son durum' })
    expect(bookmark).toHaveAttribute('aria-pressed', 'true')

    await userEvent.click(bookmark)

    await waitFor(() => expect(bookmark).toHaveAttribute('aria-pressed', 'false'))
    expect(api.savings.map((saving) => saving.method)).toEqual(['DELETE'])
  })

  it('kaydetme başarısız olursa yer imi eski haline döner ve mesaj gösterir', async () => {
    stubApi(
      () => page([article()]),
      () => new Response('{}', { status: 500 }),
    )
    renderAt('/?q=deprem')
    const bookmark = await screen.findByRole('button', { name: 'Kaydet: Deprem sonrası son durum' })

    await userEvent.click(bookmark)

    expect(await screen.findByRole('alert')).toHaveTextContent('İşlem tamamlanamadı.')
    expect(bookmark).toHaveAttribute('aria-pressed', 'false')
  })
})
