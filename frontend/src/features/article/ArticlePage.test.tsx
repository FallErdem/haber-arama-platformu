import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { I18nProvider } from 'react-aria-components'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ArticleDetail } from '../../api/articles'
import type { UserRole } from '../../api/me'
import { AccessTokenContext } from '../../auth/accessToken'
import { CurrentUserContext } from '../../auth/currentUser'
import { getHistory } from '../../lib/readingHistory'
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

/** Kaydedilenler sayfasının yerine geçer. */
function SavedStub() {
  return <p>Kaydedilenler sayfası: {useLocation().search}</p>
}

/** Gizlenen haberler ekranının yerine geçer. */
function HiddenListStub() {
  return <p>Gizlenen haberler ekranı</p>
}

/**
 * `cameFrom`: detaya gelinen sayfanın bıraktığı bilgi (arama veya Kaydedilenler). `role`: oturumdaki
 * kullanıcının rolü; "Gizle" düğmesi yalnızca yöneticiye görünür.
 */
function renderDetail(id = ID, cameFrom?: { from?: 'saved'; search: string }, role: UserRole = 'USER') {
  const currentUser = { id: 'u1', email: 'u@example.test', displayName: null, role, status: 'ACTIVE' } as const
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AccessTokenContext value="test-token">
        <CurrentUserContext value={currentUser}>
          <I18nProvider locale="tr-TR">
            <MemoryRouter initialEntries={[{ pathname: `/articles/${id}`, state: cameFrom ?? null }]}>
              <Routes>
                <Route path="/" element={<SearchStub />} />
                <Route path="/saved" element={<SavedStub />} />
                <Route path="/admin/hidden-articles" element={<HiddenListStub />} />
                <Route path="/articles/:articleId" element={<ArticlePage />} />
              </Routes>
            </MemoryRouter>
          </I18nProvider>
        </CurrentUserContext>
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

    await waitFor(() => expect(document.title).toBe('Deprem sonrası son durum · Haber Arama Platformu'))
  })

  it('"Aramaya dön" gelinen aramaya, filtreleriyle birlikte döner', async () => {
    stubDetail(detail())
    renderDetail(ID, { search: '?q=deprem&sources=TRT' })

    await userEvent.click(await screen.findByRole('link', { name: 'Aramaya dön' }))

    expect(screen.getByText('Arama sayfası: ?q=deprem&sources=TRT')).toBeInTheDocument()
  })

  it('Kaydedilenlerden gelindiyse geri bağlantısı Kaydedilenlerin aynı sayfasına döner', async () => {
    stubDetail(detail())
    renderDetail(ID, { from: 'saved', search: '?page=2' })

    await userEvent.click(await screen.findByRole('link', { name: 'Kaydedilenlere dön' }))

    expect(screen.getByText('Kaydedilenler sayfası: ?page=2')).toBeInTheDocument()
  })

  it('yer imine basınca haberi kaydeder ve yer imi basılı görünür', async () => {
    const fetchMock = stubDetail(detail())
    renderDetail()
    const bookmark = await screen.findByRole('button', { name: 'Kaydet' })
    expect(bookmark).toHaveAttribute('aria-pressed', 'false')

    await userEvent.click(bookmark)

    await waitFor(() => expect(bookmark).toHaveAttribute('aria-pressed', 'true'))
    expect(fetchMock).toHaveBeenCalledWith(`/api/v1/me/saved-articles/${ID}`, {
      method: 'PUT',
      headers: { Authorization: 'Bearer test-token' },
    })
  })

  it('kaydedilmiş haberde yer imi basılıdır; basınca haber kayıttan çıkarılır', async () => {
    const fetchMock = stubDetail(detail({ saved: true }))
    renderDetail()
    const bookmark = await screen.findByRole('button', { name: 'Kaydet' })
    expect(bookmark).toHaveAttribute('aria-pressed', 'true')

    await userEvent.click(bookmark)

    await waitFor(() => expect(bookmark).toHaveAttribute('aria-pressed', 'false'))
    expect(fetchMock).toHaveBeenCalledWith(`/api/v1/me/saved-articles/${ID}`, {
      method: 'DELETE',
      headers: { Authorization: 'Bearer test-token' },
    })
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

  it('okur "Gizle" düğmesini görmez', async () => {
    stubDetail(detail())
    renderDetail()

    await screen.findByRole('heading', { level: 1, name: 'Deprem sonrası son durum' })
    expect(screen.queryByRole('button', { name: 'Gizle' })).not.toBeInTheDocument()
  })

  it('yönetici haberi gerekçesiyle gizler; haberin yerine gizlendi mesajı ve bağlantılar çıkar (FG-YP-09)', async () => {
    const requests: { method: string; url: string; body: unknown }[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        const method = init?.method ?? 'GET'
        requests.push({ method, url, body: init?.body ? JSON.parse(init.body as string) : undefined })
        return Promise.resolve(Response.json(method === 'POST' ? { id: ID, hidden: true } : detail()))
      }),
    )
    renderDetail(ID, undefined, 'ADMIN')

    await userEvent.click(await screen.findByRole('button', { name: 'Gizle' }))
    const dialog = await screen.findByRole('dialog', { name: 'Haberi gizle' })
    const confirm = within(dialog).getByRole('button', { name: 'Gizle' })
    // Gerekçe yazılmadan onaylanamaz.
    expect(confirm).toBeDisabled()
    await userEvent.type(within(dialog).getByLabelText(/^Gerekçe/), 'Yanıltıcı başlık')
    await userEvent.click(confirm)

    const notice = await screen.findByRole('status')
    expect(within(notice).getByRole('heading', { level: 1, name: 'Haber gizlendi' })).toBeInTheDocument()
    expect(screen.queryByText('Ekipler sahada.')).not.toBeInTheDocument()
    expect(requests.filter((request) => request.method === 'POST')).toEqual([
      { method: 'POST', url: `/api/v1/admin/articles/${ID}/hide`, body: { reason: 'Yanıltıcı başlık' } },
    ])
    await userEvent.click(within(notice).getByRole('link', { name: 'Gizlenen haberler' }))
    expect(await screen.findByText('Gizlenen haberler ekranı')).toBeInTheDocument()
  })
})

describe('ArticlePage okuma araçları', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
    document.title = ''
  })

  it('açılan haberi kullanıcının okuma geçmişine ekler', async () => {
    stubDetail(detail())
    renderDetail()
    await screen.findByText('Ekipler sahada.')

    expect(getHistory('u1')).toEqual([
      expect.objectContaining({ id: ID, title: 'Deprem sonrası son durum', sourceName: 'TRT Haber', language: 'tr' }),
    ])
  })

  it('tam metin varken tahmini okuma süresini gösterir', async () => {
    stubDetail(detail())
    renderDetail()

    expect(await screen.findByText('1 dk okuma')).toBeInTheDocument()
  })

  it('yazı boyutunu büyütür, küçültür, sınırda düğmeyi kapatır ve seçimi saklar', async () => {
    stubDetail(detail())
    renderDetail()
    await screen.findByText('Ekipler sahada.')
    const body = () => document.querySelector('.article-body')!

    await userEvent.click(screen.getByRole('button', { name: 'Yazıyı büyüt' }))
    expect(body()).toHaveClass('text-xl')
    expect(localStorage.getItem('articleTextSize')).toBe('2')

    await userEvent.click(screen.getByRole('button', { name: 'Yazıyı küçült' }))
    await userEvent.click(screen.getByRole('button', { name: 'Yazıyı küçült' }))
    expect(body()).toHaveClass('text-base')
    expect(screen.getByRole('button', { name: 'Yazıyı küçült' })).toBeDisabled()
  })

  it('paylaşma menüsü olmayan tarayıcıda kaynaktaki adresi panoya kopyalar ve duyurur', async () => {
    const writeText = vi.fn(() => Promise.resolve())
    vi.stubGlobal('navigator', { ...navigator, share: undefined, clipboard: { writeText } })
    stubDetail(detail())
    renderDetail()

    await userEvent.click(await screen.findByRole('button', { name: 'Paylaş' }))

    expect(writeText).toHaveBeenCalledWith('https://www.trthaber.com/haber/1')
    expect(await screen.findByRole('status')).toHaveTextContent('Haberin bağlantısı kopyalandı.')
  })

  it('aynı konudaki en yeni haberleri haberin kendisi olmadan gösterir', async () => {
    const searches: URLSearchParams[] = []
    const related = (id: string, title: string) => ({
      id,
      title,
      summary: null,
      source: { code: 'NTV', name: 'NTV' },
      language: 'tr',
      itemType: 'ARTICLE',
      categories: ['GENERAL'],
      publishedAt: '2026-11-05T09:00:00Z',
      url: `https://www.ntv.com.tr/${id}`,
      image: null,
      otherSourcesCount: 0,
      saved: false,
    })
    vi.stubGlobal(
      'fetch',
      vi.fn((input: string) => {
        const url = new URL(input, 'http://haber.localhost')
        if (url.pathname !== '/api/v1/articles') return Promise.resolve(Response.json(detail()))
        searches.push(url.searchParams)
        return Promise.resolve(
          Response.json({
            items: [related(ID, 'Haberin kendisi'), related('0193f1a2-0000-7000-8000-000000000002', 'Benzer haber')],
            page: 0,
            size: 5,
            totalElements: 2,
            totalPages: 1,
            totalRelation: 'eq',
          }),
        )
      }),
    )
    renderDetail()

    const section = (await screen.findByRole('heading', { name: 'İlgili haberler' })).closest('section')!
    expect(within(section).getByRole('link', { name: 'Benzer haber' })).toBeInTheDocument()
    expect(within(section).queryByText('Haberin kendisi')).not.toBeInTheDocument()
    // Haberin ilk konu kategorisi (GENERAL) istenir; kendisi de gelebileceği için bir fazlası.
    expect(Object.fromEntries(searches[0])).toEqual({ categories: 'GENERAL', size: '5' })
  })
})
