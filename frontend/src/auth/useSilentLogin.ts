import { useEffect, useRef, useState } from 'react'
import { hasAuthParams, type AuthContextProps } from 'react-oidc-context'

/**
 * Sayfa açılırken, Keycloak'ta oturumu süren kullanıcıya ekran göstermeden
 * yeniden token alır. Token bellekte tutulduğu için sayfa her yenilendiğinde
 * buna ihtiyaç vardır.
 *
 * Deneme bitene kadar false döner; böylece "Giriş yap" düğmesi, oturumu
 * zaten açık olan kullanıcıya bir an bile gösterilmez.
 */
export function useSilentLogin(auth: AuthContextProps): boolean {
  // Girişten dönüş sayfasında (adreste code ve state varken) deneme yapılmaz;
  // o yanıtı AuthProvider işler. Sessiz girişin kendi çerçevesi de bu sayfayı
  // açtığından, bu kontrol çerçevenin içinde yeni bir deneme başlamasını da önler.
  const [isDone, setIsDone] = useState(() => hasAuthParams())
  const hasStarted = useRef(false)

  useEffect(() => {
    if (isDone || hasStarted.current || auth.isLoading || auth.isAuthenticated) {
      return
    }
    hasStarted.current = true
    // Oturum yoksa signinSilent hata fırlatmaz, null döner; iki durumda da deneme bitmiştir.
    void auth.signinSilent().finally(() => setIsDone(true))
  }, [auth, isDone])

  return isDone || auth.isAuthenticated
}
