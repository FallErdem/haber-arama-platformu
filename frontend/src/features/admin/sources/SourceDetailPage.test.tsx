import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { I18nProvider } from 'react-aria-components'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ManagedFeed, ManagedSource } from '../../../api/adminSources'
import { AccessTokenContext } from '../../../auth/accessToken'
import { SourceDetailPage } from './SourceDetailPage'

const SOURCE_ID = '0193f1a2-0000-7000-8000-000000000001'

function feed(overrides: Partial<ManagedFeed>): ManagedFeed {
  return {
    id: '0193f1a2-0000-7000-8000-0000000000f1',
    sourceId: SOURCE_ID,
    name: 'gundem',
    url: 'https://www.trthaber.com/gundem.rss',
    defaultCategoryCode: 'GENERAL',
    useItemCategories: false,
    fetchIntervalMinutes: 15,
    enabled: true,
    disabledReason: null,
    consecutiveFailures: 0,
    lastSuccessAt: null,
    lastError: null,
    nextFetchAt: '2026-11-20T10:00:00Z',
    manualFetchRequestedAt: null,
    version: 0,
    ...overrides,
  }
}

const FAILING = feed({ consecutiveFailures: 2, lastError: 'Zaman aşımı' })
const AUTO_DISABLED = feed({
  id: '0193f1a2-0000-7000-8000-0000000000f2',
  name: 'spor',
  enabled: false,
  disabledReason: 'AUTO',
  consecutiveFailures: 5,
  version: 4,
})

function source(overrides: Partial<ManagedSource> = {}): ManagedSource {
  return {
    id: SOURCE_ID,
    code: 'TRT',
    name: 'TRT Haber',
    homepageUrl: 'https://www.trthaber.com',
    readerType: 'RSS',
    language: 'tr',
    requestIntervalSeconds: 5,
    dailyRequestLimit: null,
    license: 'CC BY',
    attributionText: 'TRT Haber',
    feedTimeZone: null,
    enabled: true,
    purgeRequestedAt: null,
    version: 2,
    articleCount: 1240,
    feeds: [FAILING, AUTO_DISABLED],
    ...overrides,
  }
}

interface Request {
  method: string
  url: string
  body: unknown
}

/**
 * API'yi taklit eder: kaynak detayı `detail`'ın, kategoriler sabit listenin, işlem istekleri (`POST`,
 * `PATCH`) `action`'ın yanıtını alır.
 */
function stubApi(
  detail: () => Response = () => Response.json(source()),
  action: () => Response = () => Response.json({}),
) {
  const requests: Request[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      const method = init?.method ?? 'GET'
      requests.push({ method, url, body: init?.body ? JSON.parse(init.body as string) : undefined })
      if (method !== 'GET') return Promise.resolve(action())
      if (url === '/api/v1/categories') {
        return Promise.resolve(Response.json({ items: [{ code: 'SPORTS', kind: 'TOPIC', sortOrder: 40 }] }))
      }
      return Promise.resolve(detail())
    }),
  )
  return {
    actions: () => requests.filter((request) => request.method !== 'GET'),
    // Yalnızca okuma: PATCH de aynı adrese gider.
    detailRequests: () =>
      requests.filter((request) => request.method === 'GET' && request.url === `/api/v1/admin/sources/${SOURCE_ID}`),
  }
}

function renderPage(id = SOURCE_ID) {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AccessTokenContext value="test-token">
        <I18nProvider locale="tr-TR">
          <MemoryRouter initialEntries={[`/admin/sources/${id}`]}>
            <Routes>
              <Route path="/admin/sources/:sourceId" element={<SourceDetailPage />} />
            </Routes>
          </MemoryRouter>
        </I18nProvider>
      </AccessTokenContext>
    </QueryClientProvider>,
  )
}

async function feedRow(name: string) {
  return (await screen.findByText(name, { selector: 'p.font-medium' })).closest('li')!
}

describe('SourceDetailPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('beslemeleri sağlık durumlarıyla gösterir: hata sayısı, son hata, kendiliğinden kapanma (FG-YP-06, 07)', async () => {
    stubApi()
    renderPage()

    expect(await screen.findByRole('heading', { level: 1, name: 'TRT Haber' })).toBeInTheDocument()
    const failing = await feedRow('gundem')
    expect(within(failing).getByText('Etkin')).toBeInTheDocument()
    expect(within(failing).getByText('Art arda 2 hata')).toBeInTheDocument()
    expect(within(failing).getByText('Zaman aşımı')).toBeInTheDocument()
    const autoDisabled = await feedRow('spor')
    expect(within(autoDisabled).getByText('Kendiliğinden kapandı')).toBeInTheDocument()
    expect(within(autoDisabled).getByText('Art arda 5 hata')).toBeInTheDocument()
  })

  it('devre dışı kaynakta "Şimdi topla" kapalıdır', async () => {
    stubApi(() => Response.json(source({ enabled: false })))
    renderPage()

    expect(await screen.findByRole('button', { name: 'Şimdi topla' })).toBeDisabled()
  })

  it('"Şimdi topla" elle toplama ister ve kaç beslemenin sıraya alındığını söyler (FG-YP-08)', async () => {
    const api = stubApi(undefined, () => Response.json({ feedCount: 1 }, { status: 202 }))
    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: 'Şimdi topla' }))

    expect(await screen.findByRole('status')).toHaveTextContent('1 besleme okuma sırasına alındı')
    expect(api.actions()).toEqual([
      { method: 'POST', url: `/api/v1/admin/sources/${SOURCE_ID}/fetch`, body: undefined },
    ])
  })

  it('kendiliğinden kapanmış besleme sürümüyle birlikte etkinleştirilir', async () => {
    const api = stubApi()
    renderPage()
    const row = await feedRow('spor')

    await userEvent.click(within(row).getByRole('button', { name: 'Etkinleştir: spor' }))

    await waitFor(() =>
      expect(api.actions()).toEqual([
        { method: 'PATCH', url: `/api/v1/admin/feeds/${AUTO_DISABLED.id}`, body: { enabled: true, version: 4 } },
      ]),
    )
  })

  it('ayarlarda yalnızca değişen alanlar gönderilir; boşaltılan alan null olarak gider', async () => {
    const api = stubApi()
    renderPage()
    const name = await screen.findByLabelText(/^Ad/)

    await userEvent.clear(name)
    await userEvent.type(name, 'TRT Haber Ajansı')
    await userEvent.clear(screen.getByLabelText(/^Lisans/))
    await userEvent.click(screen.getByRole('button', { name: 'Kaydet' }))

    await waitFor(() =>
      expect(api.actions()).toEqual([
        {
          method: 'PATCH',
          url: `/api/v1/admin/sources/${SOURCE_ID}`,
          body: { name: 'TRT Haber Ajansı', license: null, version: 2 },
        },
      ]),
    )
  })

  it('kayıt bu arada değiştiyse bunu söyler ve kaynağı yeniden ister', async () => {
    const api = stubApi(undefined, () => new Response(JSON.stringify({ code: 'VERSION_CONFLICT' }), { status: 409 }))
    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: 'Devre dışı bırak' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('başka bir yönetici tarafından değiştirildi')
    await waitFor(() => expect(api.detailRequests()).toHaveLength(2))
  })

  it('besleme eklenir: varsayılan kategori seçilmezse null, haberlerin kategorileri kullanılır', async () => {
    const api = stubApi()
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Besleme ekle' }))
    const dialog = await screen.findByRole('dialog', { name: 'Besleme ekle' })

    await userEvent.type(within(dialog).getByLabelText(/^Ad/), 'ekonomi')
    await userEvent.type(within(dialog).getByLabelText(/^Besleme adresi/), 'https://www.trthaber.com/ekonomi.rss')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Kaydet' }))

    await waitFor(() =>
      expect(api.actions()).toEqual([
        {
          method: 'POST',
          url: `/api/v1/admin/sources/${SOURCE_ID}/feeds`,
          body: {
            name: 'ekonomi',
            url: 'https://www.trthaber.com/ekonomi.rss',
            defaultCategoryCode: null,
            useItemCategories: true,
            fetchIntervalMinutes: 15,
          },
        },
      ]),
    )
  })

  it('kaynağın haber sayısını gösterir; etkin kaynakta "İçeriği sil" önce devre dışı bırakmayı söyler', async () => {
    const api = stubApi()
    renderPage()
    expect(await screen.findByText(/1240 haber$/)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'İçeriği sil' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('İçeriği silmek için önce kaynağı devre dışı bırakın.')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(api.actions()).toEqual([])
  })

  it('devre dışı kaynağın içeriği, kodu tam yazılınca silinmek üzere istenir (FG-YP-14)', async () => {
    const api = stubApi(
      () => Response.json(source({ enabled: false })),
      () => Response.json({ articleCount: 1240 }, { status: 202 }),
    )
    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: 'İçeriği sil' }))
    const dialog = await screen.findByRole('dialog', { name: 'Kaynağın içeriğini sil' })
    expect(dialog).toHaveTextContent('TRT Haber kaynağının 1240 haberi ve görselleri kalıcı olarak silinecek')
    const confirm = within(dialog).getByRole('button', { name: 'Kalıcı olarak sil' })
    const code = within(dialog).getByLabelText(/^Onaylamak için kaynağın kodunu yazın: TRT/)
    expect(confirm).toBeDisabled()
    // Kod büyük-küçük harf dahil aynen yazılmalıdır.
    await userEvent.type(code, 'trt')
    expect(confirm).toBeDisabled()
    await userEvent.clear(code)
    await userEvent.type(code, 'TRT')
    await userEvent.click(confirm)

    expect(await screen.findByRole('status')).toHaveTextContent('İçerik silme başladı')
    expect(api.actions()).toEqual([
      { method: 'POST', url: `/api/v1/admin/sources/${SOURCE_ID}/purge`, body: { confirmationCode: 'TRT' } },
    ])
  })

  it('silme sürerken durumu gösterir; kaynak etkinleştirilemez ve yeniden silinemez', async () => {
    stubApi(() => Response.json(source({ enabled: false, purgeRequestedAt: '2026-11-21T11:02:10Z' })))
    renderPage()

    // Yüklenirken iskelet de role="status" taşır; kaynak gelip silme durumu yazılana kadar beklenir.
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('İçerik siliniyor'))
    expect(screen.getByRole('button', { name: 'Etkinleştir' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'İçeriği sil' })).toBeDisabled()
  })

  it('silme sürerken detay aralıklarla yeniden istenir; silme bitince durum kalkar ve haber sayısı 0 olur', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      let calls = 0
      const api = stubApi(() =>
        Response.json(
          calls++ === 0
            ? source({ enabled: false, purgeRequestedAt: '2026-11-21T11:02:10Z' })
            : source({ enabled: false, articleCount: 0 }),
        ),
      )
      renderPage()
      await screen.findByText('İçerik siliniyor. Bu sayfa kendiliğinden yenilenir.')

      await vi.advanceTimersByTimeAsync(5000)

      await waitFor(() => expect(screen.queryByText(/İçerik siliniyor/)).not.toBeInTheDocument())
      expect(screen.getByText(/0 haber$/)).toBeInTheDocument()
      // Silme bitince yenileme durur.
      await vi.advanceTimersByTimeAsync(15000)
      expect(api.detailRequests()).toHaveLength(2)
    } finally {
      vi.useRealTimers()
    }
  })

  it('kaynak yoksa bulunamadı sayfasını gösterir', async () => {
    stubApi(() => new Response(JSON.stringify({ code: 'NOT_FOUND' }), { status: 404 }))
    renderPage()

    expect(await screen.findByRole('heading', { level: 1, name: 'Sayfa bulunamadı' })).toBeInTheDocument()
  })
})
