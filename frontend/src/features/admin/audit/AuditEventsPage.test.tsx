import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { I18nProvider } from 'react-aria-components'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { AuditEvent } from '../../../api/adminAudit'
import { AccessTokenContext } from '../../../auth/accessToken'
import { AuditEventsPage } from './AuditEventsPage'

const ADMIN_ID = '0193f1a2-0000-7000-8000-00000000a001'
const TARGET_USER_ID = '0193f1a2-0000-7000-8000-00000000b002'

const USER_EVENT: AuditEvent = {
  id: '0193f1a2-0000-7000-8000-00000000e001',
  occurredAt: '2026-11-18T08:12:00Z',
  actorType: 'USER',
  actorUserId: ADMIN_ID,
  actorEmail: 'yonetici@example.test',
  action: 'USER_ROLE_CHANGED',
  targetType: 'USER',
  targetId: TARGET_USER_ID,
  result: 'FAILURE',
  requestId: 'istek-123',
  ipAddress: '192.0.2.10',
  details: { to: 'ADMIN', code: 'LAST_ACTIVE_ADMIN' },
}

const SYSTEM_EVENT: AuditEvent = {
  id: '0193f1a2-0000-7000-8000-00000000e002',
  occurredAt: '2026-11-18T07:00:00Z',
  actorType: 'SYSTEM',
  actorUserId: null,
  actorEmail: null,
  action: 'FEED_AUTO_DISABLED',
  targetType: 'FEED',
  targetId: '0193f1a2-0000-7000-8000-00000000f003',
  result: 'SUCCESS',
  requestId: null,
  ipAddress: null,
  details: { consecutive_failures: 5 },
}

/**
 * API'yi taklit eder. Liste ve dışa aktarma isteklerinin parametreleri ayrı ayrı kaydedilir; dışa
 * aktarma `exportResponse` ile başarılı bir dosya ya da bir hata döndürür.
 */
function stubApi(exportResponse: () => Response = csvResponse) {
  const listQueries: URLSearchParams[] = []
  const exportQueries: URLSearchParams[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn((input: string) => {
      const url = new URL(input, 'http://haber.localhost')
      if (url.pathname.endsWith('/export')) {
        exportQueries.push(url.searchParams)
        return Promise.resolve(exportResponse())
      }
      listQueries.push(url.searchParams)
      return Promise.resolve(
        Response.json({ items: [USER_EVENT, SYSTEM_EVENT], page: 0, size: 20, totalElements: 2, totalPages: 1 }),
      )
    }),
  )
  return { listQueries, exportQueries }
}

function csvResponse() {
  return new Response('﻿"id"\r\n', {
    status: 200,
    headers: { 'Content-Disposition': 'attachment; filename="audit-events-20261121-101500.csv"' },
  })
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
                path="/admin/audit-events"
                element={
                  <>
                    <AuditEventsPage />
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

describe('AuditEventsPage', () => {
  /** İndirilen dosyaların adları; jsdom'da gerçek indirme yoktur, bağlantı tıklaması yakalanır. */
  let downloads: string[]

  beforeEach(() => {
    downloads = []
    Object.defineProperty(URL, 'createObjectURL', { value: vi.fn(() => 'blob:test'), configurable: true })
    Object.defineProperty(URL, 'revokeObjectURL', { value: vi.fn(), configurable: true })
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
      downloads.push(this.download)
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('kayıtları zamanı (Türkiye saati), işlemi, kullanıcısı, hedefi, sonucu ve IP adresiyle gösterir (FG-YP-10)', async () => {
    stubApi()
    renderAt('/admin/audit-events')

    // İşlem ve sonuç adları seçim kutularının (görünmeyen) seçeneklerinde de geçer; listede aranır.
    const list = within(await screen.findByRole('list'))
    expect(list.getByText('Rol değiştirildi')).toBeInTheDocument()
    // 08:12 UTC, Türkiye'de 11:12'dir.
    expect(list.getByText('18 Kasım 2026 11:12')).toBeInTheDocument()
    expect(
      list.getByRole('button', { name: 'yonetici@example.test: bu kullanıcının kayıtlarını göster' }),
    ).toBeInTheDocument()
    expect(
      list.getByRole('button', { name: 'Kullanıcı …0000b002: bu nesnenin kayıtlarını göster' }),
    ).toBeInTheDocument()
    expect(list.getByText('Başarısız')).toBeInTheDocument()
    expect(list.getByText('192.0.2.10')).toBeInTheDocument()
    // İşçinin yazdığı kaydın kullanıcısı yoktur.
    expect(list.getByText('Besleme kendiliğinden kapandı')).toBeInTheDocument()
    expect(list.getByText('Sistem')).toBeInTheDocument()
    // Tarih seçilmemişken düğme API'nin varsayılanını söyler.
    expect(screen.getByRole('button', { name: 'Son 30 gün' })).toBeInTheDocument()
  })

  it("adresteki filtreler API'ye gider; günler Türkiye saatinin UTC anlarına çevrilir, sayfa 0'dan başlar", async () => {
    const { listQueries } = stubApi()

    renderAt('/admin/audit-events?action=USER_APPROVED&result=FAILURE&from=2026-11-01&to=2026-11-05&page=2')

    await screen.findByText('192.0.2.10')
    expect(Object.fromEntries(listQueries[0])).toEqual({
      action: 'USER_APPROVED',
      result: 'FAILURE',
      from: '2026-10-31T21:00:00.000Z',
      to: '2026-11-05T20:59:59.999Z',
      page: '1',
    })
  })

  it("adresteki bozuk değerler API'ye gönderilmez", async () => {
    const { listQueries } = stubApi()

    renderAt('/admin/audit-events?action=onay&targetType=HABER&actorUserId=kullanici&from=2026-11-10&to=2026-11-01')

    await screen.findByText('192.0.2.10')
    expect(Object.fromEntries(listQueries[0])).toEqual({ page: '0' })
  })

  it('işlem filtresi adrese yazılır ve ilk sayfaya dönülür', async () => {
    stubApi()
    renderAt('/admin/audit-events?page=3')
    await screen.findByText('192.0.2.10')

    // Seçim kutusunun adı seçili değer ve etiketten oluşur ("Tüm işlemler İşlem").
    await userEvent.click(screen.getByRole('button', { name: /İşlem$/ }))
    await userEvent.click(await screen.findByRole('option', { name: 'Kullanıcı onaylandı' }))

    expect(screen.getByTestId('location')).toHaveTextContent('?action=USER_APPROVED')
  })

  it('kullanıcıya tıklanınca liste onun kayıtlarına süzülür; etiketteki çarpı filtreyi kaldırır', async () => {
    stubApi()
    renderAt('/admin/audit-events')

    await userEvent.click(
      await screen.findByRole('button', { name: 'yonetici@example.test: bu kullanıcının kayıtlarını göster' }),
    )

    expect(screen.getByTestId('location')).toHaveTextContent(`?actorUserId=${ADMIN_ID}`)
    const chip = await screen.findByRole('button', { name: 'Filtreyi kaldır: Kullanıcı: yonetici@example.test' })
    await userEvent.click(chip)
    expect(screen.getByTestId('location')).toBeEmptyDOMElement()
  })

  it('hedefe tıklanınca liste o nesnenin kayıtlarına türüyle birlikte süzülür', async () => {
    stubApi()
    renderAt('/admin/audit-events')

    await userEvent.click(
      await screen.findByRole('button', { name: 'Kullanıcı …0000b002: bu nesnenin kayıtlarını göster' }),
    )

    expect(screen.getByTestId('location')).toHaveTextContent(`?targetType=USER&targetId=${TARGET_USER_ID}`)
    expect(screen.getByRole('button', { name: 'Filtreyi kaldır: Hedef: Kullanıcı …0000b002' })).toBeInTheDocument()
  })

  it('"Ayrıntılar" istek kimliğini ve işleme özgü alanları açar', async () => {
    stubApi()
    renderAt('/admin/audit-events')

    const toggle = await screen.findByRole('button', { name: 'Ayrıntılar: Rol değiştirildi, 18 Kasım 2026 11:12' })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByText('istek-123')).not.toBeVisible()

    await userEvent.click(toggle)

    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('istek-123')).toBeVisible()
    expect(screen.getByText('LAST_ACTIVE_ADMIN')).toBeVisible()
  })

  it('dışa aktarma aynı filtreleri sayfasız gönderir ve dosyayı sunucunun verdiği adla indirir (FG-YP-11)', async () => {
    const { exportQueries } = stubApi()
    renderAt('/admin/audit-events?action=USER_APPROVED&page=2')
    await screen.findByText('192.0.2.10')

    await userEvent.click(screen.getByRole('button', { name: 'CSV olarak dışa aktar' }))

    await waitFor(() => expect(downloads).toEqual(['audit-events-20261121-101500.csv']))
    expect(Object.fromEntries(exportQueries[0])).toEqual({ action: 'USER_APPROVED' })
  })

  it('kayıt sayısı sınırı aşılırsa tarih aralığını daraltmayı önerir', async () => {
    stubApi(() => Response.json({ status: 400, code: 'EXPORT_TOO_LARGE' }, { status: 400 }))
    renderAt('/admin/audit-events')
    await screen.findByText('192.0.2.10')

    await userEvent.click(screen.getByRole('button', { name: 'CSV olarak dışa aktar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "Dışa aktarılacak kayıt sayısı 100.000'i aşıyor. Tarih aralığını daraltın.",
    )
    expect(downloads).toEqual([])
  })
})
