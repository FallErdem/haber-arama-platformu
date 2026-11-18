import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router'
import { parseSearchState, toUrlParams, type SearchState } from './searchState'

/**
 * Arama durumunu adres çubuğundan okur ve değişiklikleri adrese yazar. Durumun tek kaynağı adrestir;
 * ayrı bir React durumu tutulmaz. Her değişiklik tarayıcı geçmişine yeni bir kayıt ekler: geri
 * düğmesi bir önceki aramaya döner.
 */
export function useSearchState() {
  const [params, setParams] = useSearchParams()
  const state = useMemo(() => parseSearchState(params), [params])

  /**
   * Durumu değiştirir. Arama ifadesi veya bir filtre değişince ilk sayfaya dönülür (eski sayfa
   * numarası yeni sonuçlar için anlamsızdır); yalnızca sayfa değiştiriliyorsa verilen sayfa geçerlidir.
   */
  const update = useCallback(
    (changes: Partial<SearchState>) => {
      setParams(toUrlParams({ ...state, page: 1, ...changes }))
    },
    [state, setParams],
  )

  /** Verilen sayfanın adresi (sayfalama bağlantıları için). */
  const hrefForPage = useCallback((page: number) => `?${toUrlParams({ ...state, page }).toString()}`, [state])

  return { state, update, hrefForPage }
}
