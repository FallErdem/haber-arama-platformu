export type UserRole = 'USER' | 'ADMIN'
export type UserStatus = 'PENDING' | 'ACTIVE' | 'PASSIVE' | 'REJECTED'

/** `GET /api/v1/me` yanıtı (API sözleşmesi, 3. bölüm). */
export interface Me {
  id: string
  email: string
  displayName: string | null
  role: UserRole
  status: UserStatus
}

/** API'nin hata yanıtı: HTTP durumu ve sözleşmedeki makine tarafından okunan kod. */
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

export async function fetchMe(accessToken: string): Promise<Me> {
  const response = await fetch('/api/v1/me', {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorCode(response))
  }
  return (await response.json()) as Me
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
