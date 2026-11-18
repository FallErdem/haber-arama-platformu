import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiGet } from './client'

function stubResponse(response: Response) {
  const fetchMock = vi.fn(() => Promise.resolve(response))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('apiGet', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("token'ı Authorization başlığında, parametreleri adreste gönderir ve JSON yanıtı döner", async () => {
    const fetchMock = stubResponse(new Response(JSON.stringify({ items: [] }), { status: 200 }))

    const body = await apiGet('/api/v1/articles', 'test-token', new URLSearchParams({ q: 'seçim', page: '0' }))

    expect(body).toEqual({ items: [] })
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/articles?q=se%C3%A7im&page=0', {
      headers: { Authorization: 'Bearer test-token' },
    })
  })

  it('parametre yoksa adrese soru işareti eklemez', async () => {
    const fetchMock = stubResponse(new Response('{}', { status: 200 }))

    await apiGet('/api/v1/sources', 'test-token', new URLSearchParams())

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/sources', expect.anything())
  })

  it('hata yanıtında HTTP durumunu ve sözleşmedeki kodu taşıyan ApiError fırlatır', async () => {
    stubResponse(
      new Response(JSON.stringify({ status: 503, title: 'Service Unavailable', code: 'SEARCH_UNAVAILABLE' }), {
        status: 503,
        headers: { 'Content-Type': 'application/problem+json' },
      }),
    )

    const error = await apiGet('/api/v1/articles', 'test-token').catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 503, code: 'SEARCH_UNAVAILABLE' })
  })

  it('hata gövdesi JSON değilse kodu boş bırakır', async () => {
    stubResponse(new Response('<html>Bad Gateway</html>', { status: 502 }))

    const error = await apiGet('/api/v1/articles', 'test-token').catch((caught: unknown) => caught)

    expect(error).toMatchObject({ status: 502, code: undefined })
  })
})
