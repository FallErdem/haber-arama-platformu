import { InMemoryWebStorage, WebStorageStateStore } from 'oidc-client-ts'
import type { AuthProviderProps } from 'react-oidc-context'

// Frontend, API ve Keycloak aynı adresin altındadır (haber.local/, /api, /auth);
// bu yüzden adresler sayfanın kendi adresinden türetilir.
const origin = window.location.origin

/**
 * Keycloak ile giriş ayarları (ADR-0014). Akış Authorization Code + PKCE'dir;
 * kütüphane başka bir akış desteklemez.
 */
export const oidcConfig: AuthProviderProps = {
  authority: `${origin}/auth/realms/haber`,
  client_id: 'haber-frontend',
  // Keycloak'ta yalnızca bu adres kayıtlıdır; birebir aynı olmalıdır.
  redirect_uri: `${origin}/oidc-callback`,
  // Sessiz yeniden giriş (sayfa yenileme) görünmeyen bir çerçevede aynı adrese döner.
  silent_redirect_uri: `${origin}/oidc-callback`,
  post_logout_redirect_uri: `${origin}/`,
  scope: 'openid profile email',
  // Token yalnızca bellekte tutulur: kalıcı depoya yazılmaz, böylece sayfaya
  // sızan bir kod onu sonradan okuyamaz. Bedeli, sayfa yenilenince token'ın
  // kaybolmasıdır; bunu sessiz yeniden giriş telafi eder (useSilentLogin).
  userStore: new WebStorageStateStore({ store: new InMemoryWebStorage() }),
  // Girişten dönünce adres çubuğundaki tek kullanımlık kod temizlenir.
  onSigninCallback: () => {
    window.history.replaceState({}, document.title, '/')
  },
}
