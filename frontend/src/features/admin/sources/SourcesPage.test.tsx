import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { I18nProvider } from 'react-aria-components'
import { MemoryRouter, Route, Routes, useParams } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { SourceOverview } from '../../../api/adminSources'
import { AccessTokenContext } from '../../../auth/accessToken'
import { SourcesPage } from './SourcesPage'

const TRT: SourceOverview = {
  id: '0193f1a2-0000-7000-8000-000000000001',
  code: 'TRT',
  name: 'TRT Haber',
  readerType: 'RSS',
  language: 'tr',
  enabled: true,
  feedCount: 3,
  failingFeedCount: 2,
  lastSuccessAt: null,
  purgeRequestedAt: null,
}

interface Request {
  method: string
  url: string
  body: unknown
}

/** API'yi taklit eder: liste sabit; ekleme isteği `create`'in yanıtını alır. */
function stubApi(
  create: () => Response = () => Response.json({ ...TRT, id: 'yeni-kaynak', feeds: [] }, { status: 201 }),
) {
  const requests: Request[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      const method = init?.method ?? 'GET'
      requests.push({ method, url, body: init?.body ? JSON.parse(init.body as string) : undefined })
      return Promise.resolve(method === 'GET' ? Response.json({ items: [TRT] }) : create())
    }),
  )
  return requests
}

function SourceDetailStub() {
  return <p>Kaynak detayı: {useParams().sourceId}</p>
}

function renderPage() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AccessTokenContext value="test-token">
        <I18nProvider locale="tr-TR">
          <MemoryRouter initialEntries={['/admin/sources']}>
            <Routes>
              <Route path="/admin/sources" element={<SourcesPage />} />
              <Route path="/admin/sources/:sourceId" element={<SourceDetailStub />} />
            </Routes>
          </MemoryRouter>
        </I18nProvider>
      </AccessTokenContext>
    </QueryClientProvider>,
  )
}

/** Kaynak ekleme penceresini açar ve zorunlu alanları doldurur. */
async function fillCreateForm() {
  await userEvent.click(await screen.findByRole('button', { name: 'Kaynak ekle' }))
  const dialog = await screen.findByRole('dialog', { name: 'Kaynak ekle' })
  await userEvent.type(within(dialog).getByLabelText(/^Kod/), 'NYT')
  await userEvent.type(within(dialog).getByLabelText(/^Ad/), 'The New York Times')
  await userEvent.type(within(dialog).getByLabelText(/^Ana sayfa adresi/), 'https://www.nytimes.com')
  return dialog
}

describe('SourcesPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('kaynakları sağlık özetiyle gösterir; hatalı besleme sayısı yazılır ve kaynak detaya bağlanır', async () => {
    stubApi()
    renderPage()

    const link = await screen.findByRole('link', { name: 'TRT Haber' })
    const row = link.closest('li')!

    expect(link).toHaveAttribute('href', `/admin/sources/${TRT.id}`)
    expect(within(row).getByText('Etkin')).toBeInTheDocument()
    expect(within(row).getByText('3 besleme')).toBeInTheDocument()
    expect(within(row).getByText('2 hatalı')).toBeInTheDocument()
    expect(within(row).getByText('Henüz başarılı toplama yok')).toBeInTheDocument()
  })

  it('kaynak eklenir ve eklenen kaynağın detayına geçilir', async () => {
    const requests = stubApi()
    renderPage()
    const dialog = await fillCreateForm()

    await userEvent.click(within(dialog).getByRole('button', { name: 'Ekle' }))

    expect(await screen.findByText('Kaynak detayı: yeni-kaynak')).toBeInTheDocument()
    expect(requests.find((request) => request.method === 'POST')).toEqual({
      method: 'POST',
      url: '/api/v1/admin/sources',
      body: {
        code: 'NYT',
        name: 'The New York Times',
        homepageUrl: 'https://www.nytimes.com',
        readerType: 'RSS',
        language: 'tr',
        requestIntervalSeconds: 5,
      },
    })
  })

  it('aynı kod başka bir kaynakta varsa bunu söyler; pencere açık kalır', async () => {
    stubApi(() => new Response(JSON.stringify({ code: 'ALREADY_EXISTS' }), { status: 409 }))
    renderPage()
    const dialog = await fillCreateForm()

    await userEvent.click(within(dialog).getByRole('button', { name: 'Ekle' }))

    expect(await within(dialog).findByRole('alert')).toHaveTextContent('başka bir kayıtta kullanılıyor')
  })

  it('API geçersiz bulduğu alanı bildirirse alan geçersiz olarak işaretlenir', async () => {
    stubApi(
      () =>
        new Response(
          JSON.stringify({ code: 'VALIDATION_FAILED', errors: [{ field: 'homepageUrl', code: 'INVALID_VALUE' }] }),
          { status: 400 },
        ),
    )
    renderPage()
    const dialog = await fillCreateForm()

    await userEvent.click(within(dialog).getByRole('button', { name: 'Ekle' }))

    await waitFor(() =>
      expect(within(dialog).getByLabelText(/^Ana sayfa adresi/)).toHaveAttribute('aria-invalid', 'true'),
    )
    expect(within(dialog).getByLabelText(/^Kod/)).not.toHaveAttribute('aria-invalid')
    expect(within(dialog).getByRole('alert')).toHaveTextContent('İşaretli alanları düzeltin.')
  })
})
