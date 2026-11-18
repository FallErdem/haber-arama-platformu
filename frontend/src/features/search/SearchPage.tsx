import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { searchArticles } from '../../api/articles'
import { useAccessToken } from '../../auth/accessToken'
import { SearchBox } from './SearchBox'
import { SearchFilters } from './SearchFilters'
import { SearchResults } from './SearchResults'
import { toApiParams } from './searchState'
import { useSearchState } from './useSearchState'

/**
 * Arama ekranı (ana sayfa; ekran akışları 5.1). Durum adres çubuğundadır (useSearchState); bu
 * bileşen durumu okur, API'ye sorar ve parçalara dağıtır.
 */
export function SearchPage() {
  const { t } = useTranslation()
  const accessToken = useAccessToken()
  const { state, update, hrefForPage } = useSearchState()

  // Aynı parametreler aynı önbellek kaydını kullanır: geri düğmesiyle dönülen arama yeniden istenmez.
  const apiQuery = toApiParams(state).toString()
  const results = useQuery({
    queryKey: ['articles', apiQuery],
    queryFn: () => searchArticles(accessToken, new URLSearchParams(apiQuery)),
    // Yeni sayfa veya filtre yüklenirken önceki sonuçlar ekranda kalır.
    placeholderData: keepPreviousData,
  })

  // Sayfa değişince sayfanın başına dönülür; ilk açılışta dokunulmaz.
  const previousPage = useRef(state.page)
  useEffect(() => {
    if (previousPage.current !== state.page) {
      previousPage.current = state.page
      window.scrollTo({ top: 0 })
    }
  }, [state.page])

  const clearFilters = () =>
    update({ sources: [], categories: [], language: undefined, from: undefined, to: undefined })

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 sm:py-10">
      <h1 className="mb-5 text-3xl font-semibold tracking-tight">{t('search.title')}</h1>
      {/* key: adresteki ifade değişince (geri düğmesi, temizleme) kutu yeniden kurulur ve onu gösterir. */}
      <SearchBox key={state.q} query={state.q} onSearch={(q) => update({ q })} />
      <SearchFilters state={state} onChange={update} />
      <SearchResults
        state={state}
        results={results}
        onChange={update}
        onClearFilters={clearFilters}
        hrefForPage={hrefForPage}
      />
    </div>
  )
}
