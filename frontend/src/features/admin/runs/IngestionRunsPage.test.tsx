import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { I18nProvider } from 'react-aria-components'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { IngestionRun } from '../../../api/adminSources'
import { AccessTokenContext } from '../../../auth/accessToken'
import { IngestionRunsPage } from './IngestionRunsPage'

const SOURCE_ID = '0193f1a2-0000-7000-8000-000000000001'

const FAILED_RUN: IngestionRun = {
  id: '0193f1a2-0000-7000-8000-0000000000r1',
  feedId: '0193f1a2-0000-7000-8000-0000000000f1',
  feedName: 'gundem',
  sourceId: SOURCE_ID,
  sourceCode: 'TRT',
  sourceName: 'TRT Haber',
  trigger: 'MANUAL',
  status: 'FAILED',
  startedAt: '2026-11-18T08:12:00Z',
  finishedAt: '2026-11-18T08:12:10Z',
  httpStatus: 500,
  itemsReceived: null,
  itemsNew: null,
  itemsDuplicate: null,
  itemsFailed: null,
  errorMessage: 'Beklenmeyen yanıt (HTTP 500)',
}

const SUCCEEDED_RUN: IngestionRun = {
  ...FAILED_RUN,
  id: '0193f1a2-0000-7000-8000-0000000000r2',
  trigger: 'SCHEDULED',
  status: 'SUCCEEDED',
  httpStatus: 200,
  itemsReceived: 20,
  itemsNew: 3,
  itemsDuplicate: 17,
  itemsFailed: 0,
  errorMessage: null,
}

/** API'yi taklit eder; geçmiş isteklerinin parametreleri `runQueries`'e yazılır. */
function stubApi() {
  const runQueries: URLSearchParams[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn((input: string) => {
      const url = new URL(input, 'http://haber.localhost')
      if (url.pathname === '/api/v1/admin/sources') {
        return Promise.resolve(Response.json({ items: [{ id: SOURCE_ID, name: 'TRT Haber' }] }))
      }
      runQueries.push(url.searchParams)
      return Promise.resolve(
        Response.json({ items: [FAILED_RUN, SUCCEEDED_RUN], page: 0, size: 20, totalElements: 2, totalPages: 1 }),
      )
    }),
  )
  return runQueries
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
                path="/admin/ingestion-runs"
                element={
                  <>
                    <IngestionRunsPage />
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

describe('IngestionRunsPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('okumaları zamanı (Türkiye saati), tetikleyicisi, sonucu ve haber sayılarıyla gösterir (FG-YP-05)', async () => {
    stubApi()
    renderAt('/admin/ingestion-runs')

    expect(await screen.findByText('Beklenmeyen yanıt (HTTP 500)')).toBeInTheDocument()
    // 08:12 UTC, Türkiye'de 11:12'dir.
    expect(screen.getAllByText('18 Kasım 2026 11:12')).toHaveLength(2)
    expect(screen.getByText('Elle')).toBeInTheDocument()
    expect(screen.getByText('Başarısız (HTTP 500)')).toBeInTheDocument()
    expect(screen.getByText('Zamanlanmış')).toBeInTheDocument()
    expect(screen.getByText('Yeni 3 · tekrar 17 · atlanan 0')).toBeInTheDocument()
  })

  it("adresteki kaynak filtresi API'ye gider; sayfa API'de 0'dan başlar", async () => {
    const runQueries = stubApi()

    renderAt(`/admin/ingestion-runs?sourceId=${SOURCE_ID}&page=2`)

    await screen.findByText('Beklenmeyen yanıt (HTTP 500)')
    expect(Object.fromEntries(runQueries[0])).toEqual({ sourceId: SOURCE_ID, page: '1' })
  })

  it('sonuç filtresi adrese yazılır ve ilk sayfaya dönülür', async () => {
    stubApi()
    renderAt('/admin/ingestion-runs?page=3')
    await screen.findByText('Beklenmeyen yanıt (HTTP 500)')

    // Seçim kutusunun adı seçili değer ve etiketten oluşur ("Tüm sonuçlar Sonuç").
    await userEvent.click(screen.getByRole('button', { name: /Sonuç$/ }))
    await userEvent.click(await screen.findByRole('option', { name: 'Başarısız' }))

    expect(screen.getByTestId('location')).toHaveTextContent('?status=FAILED')
  })
})
