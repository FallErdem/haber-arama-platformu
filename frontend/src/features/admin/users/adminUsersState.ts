import { z } from 'zod'
import type { UserRole, UserStatus } from '../../../api/me'

/**
 * Kullanıcılar ekranının durumu adres çubuğunda tutulur (arama ekranıyla aynı kural): sayfa yenilenince
 * ve geri düğmesinde filtreler korunur. Örnek: `/admin/users?status=PENDING&q=ahmet&page=2`. Adresteki
 * bozuk bir değer API'ye gönderilmez, varsayılanına döner.
 */

/** API'nin sınırıyla aynı (API sözleşmesi 6.1). */
export const MAX_QUERY_LENGTH = 200

export const USER_STATUSES: UserStatus[] = ['PENDING', 'ACTIVE', 'PASSIVE', 'REJECTED']
export const USER_ROLES: UserRole[] = ['USER', 'ADMIN']

export interface AdminUsersState {
  /** E-postada veya adda aranan metin. */
  q: string
  status: UserStatus | undefined
  role: UserRole | undefined
  /** Adreste 1'den başlar; API'de 0'dan. */
  page: number
}

const schema = z.object({
  q: z
    .string()
    .transform((value) => value.trim().slice(0, MAX_QUERY_LENGTH))
    .catch(''),
  status: z.enum(USER_STATUSES).optional().catch(undefined),
  role: z.enum(USER_ROLES).optional().catch(undefined),
  page: z.coerce.number().int().min(1).catch(1),
})

export function parseAdminUsersState(params: URLSearchParams): AdminUsersState {
  const parsed = schema.parse({
    q: params.get('q') ?? '',
    status: params.get('status') ?? undefined,
    role: params.get('role') ?? undefined,
    page: params.get('page') ?? 1,
  })
  return { q: parsed.q, status: parsed.status, role: parsed.role, page: parsed.page }
}

/** Varsayılan değerler adrese yazılmaz: aynı durum her zaman aynı adresi üretir. */
export function toUrlParams(state: AdminUsersState): URLSearchParams {
  const params = new URLSearchParams()
  if (state.q) params.set('q', state.q)
  if (state.status) params.set('status', state.status)
  if (state.role) params.set('role', state.role)
  if (state.page > 1) params.set('page', String(state.page))
  return params
}

/** `GET /api/v1/admin/users` parametreleri: adresten tek farkı sayfanın 0'dan başlaması. */
export function toApiParams(state: AdminUsersState): URLSearchParams {
  const params = toUrlParams({ ...state, page: 1 })
  params.set('page', String(state.page - 1))
  return params
}
