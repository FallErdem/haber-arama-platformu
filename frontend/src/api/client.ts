/** API'nin hata yanıtı: HTTP durumu ve sözleşmedeki makine tarafından okunan kod (API sözleşmesi 2.6). */
export class ApiError extends Error {
  readonly status: number
  readonly code: string | undefined

  constructor(status: number, code: string | undefined) {
    super(`API isteği başarısız oldu: ${status} ${code ?? ''}`.trim())
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

/**
 * API'ye token'la GET isteği gönderir ve JSON yanıtı döner. Başarısız yanıtta durumu ve hata kodunu
 * taşıyan {@link ApiError} fırlatır; arayüz hangi mesajı göstereceğine kodla karar verir.
 *
 * Yanıtın biçimi çalışma anında denetlenmez; türler API sözleşmesinden yazılmıştır ve API'nin
 * testleri sözleşmeye uyduğunu doğrular.
 */
export async function apiGet<T>(path: string, accessToken: string, query?: URLSearchParams): Promise<T> {
  const queryString = query?.toString()
  const response = await fetch(queryString ? `${path}?${queryString}` : path, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorCode(response))
  }
  return (await response.json()) as T
}

async function readErrorCode(response: Response): Promise<string | undefined> {
  try {
    const body: unknown = await response.json()
    if (typeof body === 'object' && body !== null && 'code' in body && typeof body.code === 'string') {
      return body.code
    }
  } catch {
    // Gövde JSON değilse (örneğin ağ geçidinden gelen bir hata sayfası) kod yoktur.
  }
  return undefined
}
