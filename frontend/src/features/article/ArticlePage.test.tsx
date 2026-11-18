import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { I18nProvider } from 'react-aria-components'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ArticleDetail } from '../../api/articles'
import { AccessTokenContext } from '../../auth/accessToken'
import { ArticlePage } from './ArticlePage'

const ID = '0193f1a2-0000-7000-8000-000000000001'

function detail(overrides: Partial<ArticleDetail> = {}): ArticleDetail {
  return {
    id: ID,
    title: 'Deprem sonrası son durum',
    summary: 'Bölgede çalışmalar sürüyor.',
    content: '<p>Ekipler sahada.</p><p>Çalışmalar <a href="https://example.test/afad">sürüyor</a>.</p>',
    author: 'Örnek Yazar',
    url: 'https://www.trthaber.com/haber/1',
    source: { code: 'TRT', name: 'TRT Haber', homepageUrl: 'https://www.trthaber.com', attributionText: 'TRT Haber' },
    language: 'tr',
    itemType: 'ARTICLE',
    categories: ['GENERAL', 'WORLD'],
    publishedAt: '2026-11-05T08:12:00Z',
    media: [],
    otherSources: [],
    saved: false,
    ...overrides,
  }
}

function stubDetail(response: Response | ArticleDetail) {
  const fetchMock = vi.fn(() => Promise.resolve(response instanceof Response ? response : Response.json(response)))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

/** Arama sayfasının yerine geçer: "Aramaya dön" bağlantısının nereye götürdüğünü gösterir. */
function SearchStub() {
  return <p>Arama sayfası: {useLocation().search}</p>
}

function renderDetail(id = ID, fromSearch?: string) {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AccessTokenContext value="test-token">
        <I18nProvider locale="tr-TR">
          <MemoryRouter
            initialEntries={[{ pathname: `/articles/${id}`, state: fromSearch ? { search: fromSearch } : null }]}
          >
            <Routes>
              <Route path="/" element={<SearchStub />} />
              <Route path="/articles/:articleId" element={<ArticlePage />} />
            </Routes>
          </MemoryRouter>
        </I18nProvider>
      </AccessTokenContext>
    </QueryClientProvider>,
  )
}

describe('ArticlePage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    document.title = ''
  })

  it("haberi token'la ister; başlığı, kaynağı, Türkiye saatiyle tarihi, yazarı ve kategorileri gösterir", async () => {
    const fetchMock = stubDetail(detail())

    renderDetail()

    expect(await screen.findByRole('heading', { level: 1, name: 'Deprem sonrası son durum' })).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(`/api/v1/articles/${ID}`, {
      headers: { Authorization: 'Bearer test-token' },
    })
    const article = screen.getByRole('article')
    // 08:12 UTC, Türkiye'de 11:12'dir.
    expect(within(article).getByText('5 Kasım 2026 11:12')).toHaveAttribute('dateTime', '2026-11-05T08:12:00Z')
    expect(within(article).getByText('Yazan: Örnek Yazar')).toBeInTheDocument()
    const categories = within(article).getByRole('list', { name: 'Kategoriler' })
    const categoryNames = within(categories)
      .getAllByRole('listitem')
      .map((item) => item.textContent)
    expect(categoryNames).toEqual(['Gündem', 'Dünya'])
  })

  it('tam metni paragraflarıyla gösterir; metindeki bağlantı yeni sekmede açılır', async () => {
    stubDetail(detail())

    renderDetail()

    expect(await screen.findByText('Ekipler sahada.')).toBeInTheDocument()
    const link = screen.getByRole('link', { name: 'sürüyor' })
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('tam metindeki betiği çalıştırmaz ve sayfaya koymaz', async () => {
    stubDetail(detail({ content: '<p>Metin</p><script>window.hacked = true</script><img src=x onerror="alert(1)">' }))

    renderDetail()

    await screen.findByText('Metin')
    expect(document.querySelector('.article-body script')).toBeNull()
    expect(document.querySelector('.article-body img')).toBeNull()
  })

  it('tam metin yoksa özeti gösterir (FG-AR-06)', async () => {
    stubDetail(detail({ content: null }))

    renderDetail()

    expect(await screen.findByText('Bölgede çalışmalar sürüyor.')).toBeInTheDocument()
  })

  it('metni henüz aktarılmamış haberde bunu söyler', async () => {
    stubDetail(detail({ content: null, summary: null, author: null }))

    renderDetail()

    expect(await screen.findByText(/Haberin metni henüz hazır değil/)).toBeInTheDocument()
  })

  it('görselleri altyazı ve fotoğrafçı bilgisiyle gösterir; altyazı yoksa alternatif metin başlıktır', async () => {
    stubDetail(
      detail({
        media: [
          {
            url: '/api/v1/media/m1?exp=1&sig=a',
            width: 1600,
            height: 900,
            caption: 'Bölgeden bir görüntü',
            credit: 'AA',
          },
          { url: '/api/v1/media/m2?exp=1&sig=b', width: 800, height: 600, caption: null, credit: null },
        ],
      }),
    )

    renderDetail()

    const images = await screen.findAllByRole('img')
    expect(images[0]).toHaveAttribute('src', '/api/v1/media/m1?exp=1&sig=a')
    expect(images[0]).toHaveAttribute('alt', 'Bölgeden bir görüntü')
    expect(screen.getByText('Bölgeden bir görüntü · Fotoğraf: AA')).toBeInTheDocument()
    expect(images[1]).toHaveAttribute('alt', 'Deprem sonrası son durum')
  })

  it('kaynağın adını ve özgün habere bağlantıyı gösterir; ikisi de yeni sekmede açılır (FG-AR-07)', async () => {
    stubDetail(detail())

    renderDetail()

    const original = await screen.findByRole('link', { name: 'Haberin tamamını kaynağında oku' })
    expect(original).toHaveAttribute('href', 'https://www.trthaber.com/haber/1')
    expect(original).toHaveAttribute('rel', 'noopener noreferrer')
    const source = screen.getByRole('complementary', { name: 'Kaynak' })
    expect(within(source).getByRole('link', { name: 'TRT Haber' })).toHaveAttribute('href', 'https://www.trthaber.com')
    expect(within(source).queryByText(/Creative Commons/)).not.toBeInTheDocument()
  })

  it('Global Voices haberinde lisans bilgisini gösterir ve metni İngilizce olarak işaretler', async () => {
    stubDetail(
      detail({
        language: 'en',
        source: {
          code: 'GLOBALVOICES',
          name: 'Global Voices',
          homepageUrl: 'https://globalvoices.org',
          attributionText: 'Global Voices',
        },
      }),
    )

    renderDetail()

    expect(await screen.findByText(/Creative Commons Atıf \(CC BY\)/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Global Voices atıf politikası' })).toHaveAttribute(
      'href',
      'https://globalvoices.org/about/global-voices-attribution-policy/',
    )
    expect(screen.getByRole('article')).toHaveAttribute('lang', 'en')
  })

  it('sekmenin başlığına haberin başlığını yazar', async () => {
    stubDetail(detail())

    renderDetail()

    await waitFor(() => expect(document.title).toBe('Deprem sonrası son durum · Haber Arama'))
  })

  it('"Aramaya dön" gelinen aramaya, filtreleriyle birlikte döner', async () => {
    stubDetail(detail())
    renderDetail(ID, '?q=deprem&sources=TRT')

    await userEvent.click(await screen.findByRole('link', { name: 'Aramaya dön' }))

    expect(screen.getByText('Arama sayfası: ?q=deprem&sources=TRT')).toBeInTheDocument()
  })

  it('gizlenmiş veya kayıtlı olmayan haberde bulunamadı sayfasını gösterir', async () => {
    stubDetail(new Response(JSON.stringify({ status: 404, code: 'NOT_FOUND' }), { status: 404 }))

    renderDetail()

    expect(await screen.findByRole('heading', { level: 1, name: 'Sayfa bulunamadı' })).toBeInTheDocument()
  })

  it("kimlik UUID değilse API'ye sormadan bulunamadı sayfasını gösterir", () => {
    const fetchMock = stubDetail(detail())

    renderDetail('haber-1')

    expect(screen.getByRole('heading', { level: 1, name: 'Sayfa bulunamadı' })).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('arama indeksi kapalıyken metinlerin alınamadığını söyler ve yeniden denemeye izin verir', async () => {
    stubDetail(new Response(JSON.stringify({ status: 503, code: 'SEARCH_UNAVAILABLE' }), { status: 503 }))

    renderDetail()

    expect(await screen.findByRole('alert')).toHaveTextContent('Haber metinleri şu an alınamıyor.')
    expect(screen.getByRole('button', { name: 'Yeniden dene' })).toBeInTheDocument()
  })
})
