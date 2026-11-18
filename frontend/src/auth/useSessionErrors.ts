import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { ApiError } from '../api/client'

/** Hesabın durumunu bildiren 403 kodları (API sözleşmesi 2.6). */
const ACCOUNT_STATUS_CODES = new Set(['USER_PENDING_APPROVAL', 'USER_REJECTED', 'USER_PASSIVE'])

/**
 * Oturumla ilgili API hatalarını tek yerden ele alır (ekran akışları 2. bölüm). Her sayfanın kendi
 * hatasını ayrıca yazması gerekmez; TanStack Query önbelleğindeki bütün isteklerin hataları dinlenir.
 *
 * - 401 (token geçersiz veya süresi dolmuş): `onUnauthenticated` çağrılır; kullanıcı Keycloak'a
 *   yönlendirilir. Token süresi dolmadan sessizce yenilendiği için bu yalnızca yenileme başarısız
 *   olursa görülür.
 * - 403 ve hesap kodu (örneğin oturum ortasında pasif yapılan kullanıcı, ekran akışları 4.6):
 *   kullanıcı bilgisi yeniden istenir; durum artık aktif olmadığından uygulama hesap durumu ekranına
 *   geçer.
 */
export function useSessionErrors(onUnauthenticated: () => void): void {
  const queryClient = useQueryClient()
  // Aynı anda birden fazla istek 401 alabilir; yönlendirme bir kez başlatılır.
  const isRedirecting = useRef(false)

  useEffect(
    () =>
      // subscribe, aboneliği bitiren fonksiyonu döner; bileşen kaldırılınca React onu çağırır.
      queryClient.getQueryCache().subscribe((event) => {
        if (event.type !== 'updated' || event.action.type !== 'error') return
        const { error } = event.action
        if (!(error instanceof ApiError)) return

        if (error.status === 401 && !isRedirecting.current) {
          isRedirecting.current = true
          onUnauthenticated()
        } else if (error.status === 403 && error.code !== undefined && ACCOUNT_STATUS_CODES.has(error.code)) {
          void queryClient.invalidateQueries({ queryKey: ['me'] })
        }
      }),
    [queryClient, onUnauthenticated],
  )
}
