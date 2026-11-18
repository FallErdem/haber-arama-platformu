import { createContext, useContext } from 'react'

/**
 * Giriş yapmış kullanıcının erişim token'ı. AuthenticatedApp sağlar; sayfalar API isteklerinde
 * `useAccessToken` ile alır. Token yenilendiğinde (kütüphane süresi dolmadan sessizce yeniler) değer
 * de değişir ve sonraki istekler yeni token'la gider.
 */
export const AccessTokenContext = createContext<string | null>(null)

export function useAccessToken(): string {
  const accessToken = useContext(AccessTokenContext)
  if (accessToken === null) {
    // Yalnızca bir programlama hatasında olur: sayfa, girişten sonraki ağacın dışında kullanılmıştır.
    throw new Error('useAccessToken, AccessTokenContext sağlanmadan kullanıldı')
  }
  return accessToken
}
