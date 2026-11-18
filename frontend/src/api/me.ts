import { apiGet } from './client'

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

export function fetchMe(accessToken: string): Promise<Me> {
  return apiGet<Me>('/api/v1/me', accessToken)
}
