import { SearchIcon, XIcon } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button as AriaButton, SearchField } from 'react-aria-components'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { MAX_QUERY_LENGTH } from './searchState'

interface SearchBoxProps {
  /** Adresteki arama ifadesi. Değişince bileşen yeniden kurulur (`key`), kutu adresteki değeri gösterir. */
  query: string
  onSearch: (query: string) => void
  /** Kutunun erişilebilir adı ve yer tutucu metni; verilmezse haber aramasınınkiler. */
  label?: string
  placeholder?: string
}

/**
 * Arama kutusu. Yazılan metin "Ara" düğmesine veya Enter'a basılınca adrese yazılır; her harfte
 * arama yapılmaz (her harf bir API isteği ve bir geçmiş kaydı olurdu). Yönetim panelindeki kullanıcı
 * araması da aynı kutuyu kullanır.
 */
export function SearchBox({ query, onSearch, label, placeholder }: SearchBoxProps) {
  const { t } = useTranslation()
  const [text, setText] = useState(query)

  return (
    <form
      role="search"
      className="flex gap-2"
      onSubmit={(event) => {
        event.preventDefault()
        onSearch(text)
      }}
    >
      {/* SearchField: Escape kutuyu temizler; içindeki düğme kendiliğinden "temizle" düğmesi olur. */}
      <SearchField
        aria-label={label ?? t('search.queryLabel')}
        value={text}
        onChange={setText}
        onClear={() => onSearch('')}
        className="group relative flex-1"
      >
        <SearchIcon
          aria-hidden
          className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
        />
        <Input
          placeholder={placeholder ?? t('search.queryPlaceholder')}
          maxLength={MAX_QUERY_LENGTH}
          className="h-11 bg-card pr-10 pl-9 text-base md:text-base [&::-webkit-search-cancel-button]:hidden"
        />
        <AriaButton
          aria-label={t('search.clearQuery')}
          className="absolute top-1/2 right-2 flex size-7 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground outline-none group-data-empty:hidden hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          <XIcon aria-hidden className="size-4" />
        </AriaButton>
      </SearchField>
      <Button type="submit" className="h-11 px-5">
        {t('search.submit')}
      </Button>
    </form>
  )
}
