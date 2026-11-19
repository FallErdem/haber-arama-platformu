import { apiGet, apiSendJson } from './client'
import type { UserRole, UserStatus } from './me'

/** Yönetim panelindeki bir kullanıcı (API sözleşmesi 6.1). */
export interface AdminUser {
  id: string
  email: string
  displayName: string | null
  role: UserRole
  status: UserStatus
  createdAt: string
  /** Rol veya durum değiştirirken geri gönderilir; kayıt bu arada değiştiyse API `VERSION_CONFLICT` döner. */
  version: number
}

/** Sayfalı liste (API sözleşmesi 2.4). `page` 0'dan başlar. */
export interface AdminUsersResponse {
  items: AdminUser[]
  page: number
  size: number
  totalElements: number
  totalPages: number
}

/** Rol ve durum değişikliği; verilmeyen alan değişmez. */
export interface UserChange {
  role?: UserRole
  status?: 'ACTIVE' | 'PASSIVE'
  version: number
}

const PATH = '/api/v1/admin/users'

/** Kullanıcı listesi. `query`: `status`, `role`, `q`, `page` (0'dan başlar). */
export function fetchAdminUsers(accessToken: string, query: URLSearchParams): Promise<AdminUsersResponse> {
  return apiGet<AdminUsersResponse>(PATH, accessToken, query)
}

export function approveUser(accessToken: string, userId: string): Promise<AdminUser> {
  return apiSendJson<AdminUser>('POST', `${PATH}/${encodeURIComponent(userId)}/approve`, accessToken)
}

export function rejectUser(accessToken: string, userId: string): Promise<AdminUser> {
  return apiSendJson<AdminUser>('POST', `${PATH}/${encodeURIComponent(userId)}/reject`, accessToken)
}

export function changeUser(accessToken: string, userId: string, change: UserChange): Promise<AdminUser> {
  return apiSendJson<AdminUser>('PATCH', `${PATH}/${encodeURIComponent(userId)}`, accessToken, change)
}
