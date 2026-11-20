/**
 * API'nin hata yanıtı: HTTP durumu, sözleşmedeki makine tarafından okunan kod ve doğrulama hatasında
 * geçersiz alanların adları (API sözleşmesi 2.6). Formlar geçersiz alanı bu adlarla işaretler.
 */
export class ApiError extends Error {
  readonly status: number
  readonly code: string | undefined
  readonly fields: string[]

  constructor(status: number, code: string | undefined, fields: string[] = []) {
    super(`API isteği başarısız oldu: ${status} ${code ?? ''}`.trim())
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.fields = fields
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
    throw await toApiError(response)
  }
  return (await response.json()) as T
}

/**
 * API'ye token'la gövdesiz bir değiştirme isteği (`PUT`, `DELETE`) gönderir. Başarılı yanıt
 * `204 No Content`'tir, okunacak bir şey yoktur; başarısız yanıtta {@link ApiError} fırlatır.
 */
export async function apiSend(method: 'PUT' | 'DELETE', path: string, accessToken: string): Promise<void> {
  const response = await fetch(path, { method, headers: { Authorization: `Bearer ${accessToken}` } })
  if (!response.ok) {
    throw await toApiError(response)
  }
}

/**
 * API'ye token'la, gövdesi JSON olabilen bir işlem isteği (`POST`, `PATCH`) gönderir ve JSON yanıtı
 * döner. Başarısız yanıtta {@link ApiError} fırlatır; arayüz mesajı hata kodundan seçer
 * (`LAST_ACTIVE_ADMIN` gibi).
 */
export async function apiSendJson<T>(
  method: 'POST' | 'PATCH',
  path: string,
  accessToken: string,
  body?: unknown,
): Promise<T> {
  const response = await fetch(path, {
    method,
    headers:
      body === undefined
        ? { Authorization: `Bearer ${accessToken}` }
        : { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) {
    throw await toApiError(response)
  }
  return (await response.json()) as T
}

/**
 * Başarısız bir isteğin yeniden denenip denenmeyeceği (TanStack Query'nin `retry` ayarı; bütün
 * isteklerin varsayılanı, bkz. main.tsx). Sunucu yanıt verdiyse (404, 503...) durumu bellidir:
 * yeniden denenmez, kullanıcı mesajı hemen görür ve isterse "Yeniden dene"ye basar. Yalnızca ağ
 * hataları (bağlantı kopması) iki kez daha denenir. Kütüphanenin varsayılanı her hatayı üç kez
 * dener; kapalı bir arama indeksinde hata mesajı yaklaşık 7 saniye gecikirdi.
 */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  return !(error instanceof ApiError) && failureCount < 2
}

/** Başarısız yanıttan hata nesnesini üretir. */
async function toApiError(response: Response): Promise<ApiError> {
  try {
    const body: unknown = await response.json()
    if (typeof body === 'object' && body !== null) {
      const code = 'code' in body && typeof body.code === 'string' ? body.code : undefined
      return new ApiError(response.status, code, invalidFields(body))
    }
  } catch {
    // Gövde JSON değilse (örneğin ağ geçidinden gelen bir hata sayfası) kod yoktur.
  }
  return new ApiError(response.status, undefined)
}

/** Doğrulama hatasındaki `errors` listesinden alan adları (`[{ "field": "code", ... }]` → `['code']`). */
function invalidFields(body: object): string[] {
  if (!('errors' in body) || !Array.isArray(body.errors)) {
    return []
  }
  return body.errors.flatMap((error: unknown) =>
    typeof error === 'object' && error !== null && 'field' in error && typeof error.field === 'string'
      ? [error.field]
      : [],
  )
}
