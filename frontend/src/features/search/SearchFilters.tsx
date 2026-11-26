import { useQuery } from '@tanstack/react-query'
import { cn } from 'cn'
import { ZapIcon } from 'lucide-react'
import type { Key } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { fetchSources } from '../../api/catalog'
import { useAccessToken } from '../../auth/accessToken'
import { Button } from '../../components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { Toggle } from '../../components/ui/toggle'
import { DateRangeFilter } from './DateRangeFilter'
import { FilterSelect } from './FilterSelect'
import type { SearchLanguage, SearchState } from './searchState'
// Son Dakika, kategori listesinde değil ayrı bir düğmeyle seçilir (ekran akışları 5.1).
import { BREAKING, CATALOG_STALE_TIME, useCategories } from './useCategories'

interface SearchFiltersProps {
  state: SearchState
  onChange: (changes: Partial<SearchState>) => void
}

/** Filtreler: kaynak, kategori, dil, tarih aralığı ve Son Dakika (FG-AR-02, FG-AR-12). */
export function SearchFilters({ state, onChange }: SearchFiltersProps) {
  const { t } = useTranslation()
  const accessToken = useAccessToken()
  const sources = useQuery({
    queryKey: ['sources'],
    queryFn: () => fetchSources(accessToken),
    staleTime: CATALOG_STALE_TIME,
  })
  const categories = useCategories()

  const isBreaking = state.categories.includes(BREAKING)
  const topicCategories = state.categories.filter((code) => code !== BREAKING)
  const hasFilters =
    state.sources.length > 0 ||
    state.categories.length > 0 ||
    state.language !== undefined ||
    state.from !== undefined ||
    state.to !== undefined

  return (
    <div role="group" aria-label={t('search.filters.label')} className="mt-4 flex flex-wrap items-center gap-2">
      <FilterSelect
        label={t('search.filters.source')}
        options={(sources.data ?? []).map((source) => ({ id: source.code, name: source.name }))}
        value={state.sources}
        onChange={(codes) => onChange({ sources: codes })}
      />
      <FilterSelect
        label={t('search.filters.category')}
        // API kategorileri arayüzdeki sırasıyla döner (sortOrder); adları dil dosyasından gelir.
        options={(categories.data ?? [])
          .filter((category) => category.kind === 'TOPIC')
          .map((category) => ({ id: category.code, name: t(`categories.${category.code}`) }))}
        value={topicCategories}
        onChange={(codes) => onChange({ categories: isBreaking ? [...codes, BREAKING] : codes })}
      />
      <LanguageFilter value={state.language} onChange={(language) => onChange({ language })} />
      <DateRangeFilter from={state.from} to={state.to} onChange={(from, to) => onChange({ from, to })} />
      <Toggle
        isSelected={isBreaking}
        onChange={(isSelected) =>
          onChange({ categories: isSelected ? [...topicCategories, BREAKING] : topicCategories })
        }
      >
        <ZapIcon aria-hidden />
        {t('search.filters.breaking')}
      </Toggle>
      {hasFilters && (
        <Button
          variant="link"
          onPress={() => onChange({ sources: [], categories: [], language: undefined, from: undefined, to: undefined })}
        >
          {t('search.filters.clear')}
        </Button>
      )}
    </div>
  )
}

const ALL_LANGUAGES = 'all'

function LanguageFilter({
  value,
  onChange,
}: {
  value: SearchLanguage | undefined
  onChange: (language: SearchLanguage | undefined) => void
}) {
  const { t } = useTranslation()

  return (
    <Select
      aria-label={t('search.filters.language')}
      value={value ?? ALL_LANGUAGES}
      onChange={(key: Key | null) => onChange(key === 'tr' || key === 'en' ? key : undefined)}
    >
      <SelectTrigger className={cn('w-auto', value && 'border-primary text-primary')}>
        <SelectValue>{value ? t(`languages.${value}`) : t('search.filters.language')}</SelectValue>
      </SelectTrigger>
      <SelectContent>
        <SelectItem id={ALL_LANGUAGES}>{t('search.filters.allLanguages')}</SelectItem>
        <SelectItem id="tr">{t('languages.tr')}</SelectItem>
        <SelectItem id="en">{t('languages.en')}</SelectItem>
      </SelectContent>
    </Select>
  )
}
