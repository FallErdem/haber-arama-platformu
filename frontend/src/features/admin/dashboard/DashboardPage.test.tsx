import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import { I18nProvider } from 'react-aria-components'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Stats } from '../../../api/adminStats'
import { AccessTokenContext } from '../../../auth/accessToken'
import { DashboardPage } from './DashboardPage'

const MINUTE = 60_000

function stats(overrides: Partial<Stats> = {}): Stats {
  return {
    articles: {
      total: 4321,
      last24h: 215,
      bySource: [
        { code: 'CNNTURK', name: 'CNN Türk', total: 1725, last24h: 96 },
        { code: 'GLOBALVOICES', name: 'Global Voices', total: 0, last24h: 0 },
        { code: 'TRT', name: 'TRT Haber', total: 2596, last24h: 119 },
      ],
    },
    users: { PENDING: 2, ACTIVE: 12, PASSIVE: 1, REJECTED: 0 },
    feeds: { enabled: 41, failing: 0, disabledAuto: 0 },
    searchIndex: { pendingOutboxEvents: 0 },
    components: {
      database: 'UP',
      elasticsearch: 'UP',
      objectStorage: 'UP',
      workerLastActivityAt: new Date(Date.now() - 3 * MINUTE).toISOString(),
    },
    ...overrides,
  }
}

/** API'yi taklit eder; her istek `response`'un verdiği panoyu alır. İstek sayısı döner. */
function stubApi(response: () => Stats = () => stats()) {
  const fetchMock = vi.fn(() => Promise.resolve(Response.json(response())))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function renderPage() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AccessTokenContext value="test-token">
        <I18nProvider locale="tr-TR">
          <MemoryRouter initialEntries={['/admin']}>
            <DashboardPage />
          </MemoryRouter>
        </I18nProvider>
      </AccessTokenContext>
    </QueryClientProvider>,
  )
}

/** Bir özet kutusu: başlığıyla bulunur. */
async function card(label: string) {
  return (await screen.findByText(label, { selector: 'dt' })).parentElement!
}

describe('DashboardPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('haber, kullanıcı, besleme ve arama indeksi özetlerini Türkçe sayı biçimiyle gösterir (FG-YP-12)', async () => {
    stubApi()
    renderPage()

    const articles = await card('Haberler')
    expect(articles).toHaveTextContent('4.321')
    expect(articles).toHaveTextContent('Son 24 saatte 215 yeni haber')
    const users = await card('Kullanıcılar')
    expect(users).toHaveTextContent('12aktif')
    expect(users).toHaveTextContent('1 pasif · 0 reddedilen')
    expect(await card('Beslemeler')).toHaveTextContent('Hatalı besleme yok')
    expect(await card('Arama indeksi')).toHaveTextContent('Bütün değişiklikler aktarıldı')
  })

  it('onay bekleyen kullanıcı varsa onay bekleyenleri gösteren Kullanıcılar ekranına bağlantı verir', async () => {
    stubApi()
    renderPage()

    expect(await screen.findByRole('link', { name: '2 kullanıcı onay bekliyor' })).toHaveAttribute(
      'href',
      '/admin/users?status=PENDING',
    )
  })

  it('hatalı ve kendiliğinden kapanmış beslemeleri kaynaklar ekranına bağlantıyla söyler', async () => {
    stubApi(() => stats({ feeds: { enabled: 40, failing: 1, disabledAuto: 2 } }))
    renderPage()

    expect(await screen.findByRole('link', { name: '1 hatalı · 2 kendiliğinden kapandı' })).toHaveAttribute(
      'href',
      '/admin/sources',
    )
  })

  it('kaynak bazında haber sayılarını tabloda gösterir; haberi olmayan kaynak da yer alır', async () => {
    stubApi()
    renderPage()

    const table = await screen.findByRole('table')
    const rows = within(table).getAllByRole('row')
    expect(rows.map((row) => row.textContent)).toEqual([
      'KaynakToplamSon 24 saat',
      'CNN Türk1.72596',
      'Global Voices00',
      'TRT Haber2.596119',
    ])
  })

  it('bileşenlerin durumunu yazıyla gösterir; ulaşılamayan bileşen ayrıca işaretlenir', async () => {
    stubApi(() => stats({ components: { ...stats().components, elasticsearch: 'DOWN' } }))
    renderPage()

    const system = await screen.findByRole('region', { name: 'Sistem durumu' })
    const items = within(system).getAllByRole('listitem')
    expect(items.map((item) => item.textContent)).toEqual([
      'VeritabanıÇalışıyor',
      'Arama (Elasticsearch)Ulaşılamıyor',
      'Görseller (MinIO)Çalışıyor',
      'Arka plan işleriSon etkinlik 3 dakika önce',
    ])
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('işçinin son etkinliği 30 dakikadan eskiyse uyarır', async () => {
    const twoHoursAgo = new Date(Date.now() - 120 * MINUTE).toISOString()
    stubApi(() => stats({ components: { ...stats().components, workerLastActivityAt: twoHoursAgo } }))
    renderPage()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Arka plan işleri çalışmıyor olabilir: son etkinlik 2 saat önce.',
    )
  })

  it('işçi hiç çalışmadıysa bunu söyler', async () => {
    stubApi(() => stats({ components: { ...stats().components, workerLastActivityAt: null } }))
    renderPage()

    expect(await screen.findByRole('alert')).toHaveTextContent('Arka plan işleri henüz hiç çalışmadı.')
    expect(screen.getByText('Henüz çalışmadı')).toBeInTheDocument()
  })

  it('30 saniyede bir kendiliğinden yenilenir', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const fetchMock = stubApi()
    renderPage()
    await card('Haberler')

    await vi.advanceTimersByTimeAsync(30_000)

    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
