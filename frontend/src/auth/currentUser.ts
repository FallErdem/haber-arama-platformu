import { createContext, useContext } from 'react'
import type { Me } from '../api/me'

/**
 * Oturumdaki aktif kullanıcı (`GET /api/v1/me`). AuthenticatedApp sağlar; yalnızca yöneticiye görünen
 * menü ve sayfalar rolü buradan okur. Bu yalnızca bir kolaylıktır: yetki kontrolü backend'dedir
 * (ekran akışları 2. bölüm).
 */
export const CurrentUserContext = createContext<Me | null>(null)

export function useCurrentUser(): Me {
  const user = useContext(CurrentUserContext)
  if (user === null) {
    // Yalnızca bir programlama hatasında olur: sayfa, girişten sonraki ağacın dışında kullanılmıştır.
    throw new Error('useCurrentUser, CurrentUserContext sağlanmadan kullanıldı')
  }
  return user
}
