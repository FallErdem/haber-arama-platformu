import { cn } from 'cn'
import type { Key } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'

export interface FilterOption {
  id: string
  name: string
}

interface FilterSelectProps {
  label: string
  options: FilterOption[]
  value: string[]
  onChange: (value: string[]) => void
}

/**
 * Çoklu seçimli filtre (kaynak, kategori). Düğmede seçim yoksa filtrenin adı, bir seçim varsa onun
 * adı, birden fazlaysa adı ve seçim sayısı yazar ("Kaynak · 2"). Seçim varken düğme vurgu renginde
 * görünür; hangi filtrelerin uygulandığı bir bakışta anlaşılır.
 */
export function FilterSelect({ label, options, value, onChange }: FilterSelectProps) {
  const { t } = useTranslation()
  const selectedName = value.length === 1 ? options.find((option) => option.id === value[0])?.name : undefined
  const display =
    value.length === 0 ? label : (selectedName ?? t('search.filters.selectedCount', { label, count: value.length }))

  return (
    <Select
      aria-label={label}
      selectionMode="multiple"
      value={value}
      onChange={(keys: Key[]) => onChange(keys.map(String))}
    >
      <SelectTrigger className={cn('w-auto', value.length > 0 && 'border-primary text-primary')}>
        <SelectValue>{display}</SelectValue>
      </SelectTrigger>
      <SelectContent>
        {options.map((option) => (
          <SelectItem key={option.id} id={option.id}>
            {option.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
