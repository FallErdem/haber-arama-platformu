import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import { I18nProvider } from 'react-aria-components'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { MarketQuote } from '../../api/marketQuotes'
import { AccessTokenContext } from '../../auth/accessToken'
import { MarketQuotes } from './MarketQuotes'

function quote(overrides: Partial<MarketQuote>): MarketQuote {
  return {
    code: 'USD',
    price: 50.7851,
    changePercent: 0.13,
    currency: 'TRY',
    marketTime: '2026-11-27T12:30:37Z',
    fetchedAt: '2026-11-27T12:31:02Z',
    ...overrides,
  }
}

/** `/api/v1/market-quotes` verilen yanıtı döner ve istekleri kaydeder. */
function stubApi(response: () => Response) {
  const fetchMock = vi.fn(() => Promise.resolve(response()))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function renderBox() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const { container } = render(
    <QueryClientProvider client={queryClient}>
      <AccessTokenContext value="test-token">
        <I18nProvider locale="tr-TR">
          <MarketQuotes />
        </I18nProvider>
      </AccessTokenContext>
    </QueryClientProvider>,
  )
  /** İsteğin bitmesini bekler: kutu yüklenirken de boştur, "görünmez" kontrolü istek bittikten sonra anlamlıdır. */
  const requestFinished = (status: 'success' | 'error') =>
    waitFor(() => expect(queryClient.getQueryState(['market-quotes'])?.status).toBe(status))
  return { container, requestFinished }
}

/** Bir değerin kutudaki bölümü: adı ve altındaki iki satır (fiyat, değişim). */
function item(name: string) {
  const term = screen.getByText(name)
  const group = term.closest('div')
  if (group === null) throw new Error(`${name} için grup bulunamadı`)
  return group
}

describe('MarketQuotes', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('değerleri sabit sırayla gösterir; tanınmayan kod gösterilmez', async () => {
    const fetchMock = stubApi(() =>
      Response.json({
        items: [
          quote({ code: 'BRENT', price: 91.69, currency: 'USD' }),
          quote({ code: 'BIST100', price: 11026.26 }),
          quote({ code: 'XAU', price: 1 }),
          quote({ code: 'USD' }),
          quote({ code: 'GRAM_GOLD', price: 5989.81 }),
          quote({ code: 'EUR', price: 55.74 }),
          quote({ code: 'GOLD_OUNCE', price: 3692.7, currency: 'USD' }),
          quote({ code: 'BITCOIN', price: 61371, currency: 'USD' }),
          quote({ code: 'SILVER_OUNCE', price: 44.06, currency: 'USD' }),
        ],
      }),
    )

    renderBox()

    const list = await screen.findByRole('region', { name: 'Piyasalar' })
    const names = within(list)
      .getAllByRole('term')
      .map((term) => term.textContent)
    expect(names).toEqual([
      'Dolar',
      'Euro',
      'Gram altın',
      'Ons altın',
      'Ons gümüş',
      'BIST 100',
      'Brent petrol',
      'Bitcoin',
    ])
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/market-quotes', {
      headers: { Authorization: 'Bearer test-token' },
    })
  })

  it('fiyatı Türkçe biçimde, dolar cinsinden olanları $ ile gösterir', async () => {
    stubApi(() =>
      Response.json({
        items: [
          quote({ code: 'USD', price: 50.7851 }),
          quote({ code: 'BIST100', price: 11026.26 }),
          quote({ code: 'GOLD_OUNCE', price: 3692.7, currency: 'USD' }),
        ],
      }),
    )

    renderBox()

    await screen.findByRole('region', { name: 'Piyasalar' })
    expect(within(item('Dolar')).getByText('50,79')).toBeInTheDocument()
    expect(within(item('BIST 100')).getByText('11.026,26')).toBeInTheDocument()
    expect(within(item('Ons altın')).getByText('$3.692,70')).toBeInTheDocument()
  })

  it('yükselişi ▲, düşüşü ▼ ile gösterir ve yönü ekran okuyucuya kelimeyle söyler', async () => {
    stubApi(() =>
      Response.json({
        items: [
          quote({ code: 'USD', changePercent: 0.13 }),
          quote({ code: 'BRENT', changePercent: -1.64, currency: 'USD' }),
          quote({ code: 'EUR', changePercent: 0 }),
        ],
      }),
    )

    renderBox()

    await screen.findByRole('region', { name: 'Piyasalar' })
    expect(item('Dolar')).toHaveTextContent('▲ yükseliş %0,13')
    expect(item('Brent petrol')).toHaveTextContent('▼ düşüş %1,64')
    // Değişim yoksa ok ve yön kelimesi de yoktur.
    expect(item('Euro')).toHaveTextContent('%0,00')
    expect(item('Euro')).not.toHaveTextContent(/▲|▼|yükseliş|düşüş/)
  })

  it('alt satırda en yeni çekim saatini ve kaynağı gösterir', async () => {
    stubApi(() =>
      Response.json({
        items: [
          quote({ code: 'USD', fetchedAt: '2026-11-27T12:31:02Z' }),
          // Bu değer bir önceki turda kalmış (o turda okunamamış).
          quote({ code: 'EUR', fetchedAt: '2026-11-27T12:16:00Z' }),
        ],
      }),
    )

    renderBox()

    // Saat, testin çalıştığı bilgisayarın saat dilimine göre biçimlenir; beklenen değer aynı biçimle üretilir.
    const time = new Intl.DateTimeFormat('tr-TR', { hour: '2-digit', minute: '2-digit' }).format(
      new Date('2026-11-27T12:31:02Z'),
    )
    expect(await screen.findByText(`Son güncelleme ${time} · Yahoo Finance`)).toBeInTheDocument()
  })

  it('henüz değer yoksa kutu görünmez', async () => {
    stubApi(() => Response.json({ items: [] }))

    const { container, requestFinished } = renderBox()

    await requestFinished('success')
    expect(container).toBeEmptyDOMElement()
  })

  it('istek başarısız olursa kutu görünmez; hata mesajı gösterilmez', async () => {
    stubApi(() => Response.json({ code: 'INTERNAL_ERROR' }, { status: 500 }))

    const { container, requestFinished } = renderBox()

    await requestFinished('error')
    expect(container).toBeEmptyDOMElement()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
