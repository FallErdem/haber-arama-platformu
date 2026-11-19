import { cn } from 'cn'
import { BookmarkIcon } from 'lucide-react'
import { ToggleButton } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { buttonVariants } from '../../components/ui/button-variants'

interface BookmarkToggleProps {
  isSaved: boolean
  onChange: (saved: boolean) => void
  isDisabled?: boolean
  /** Listelerde haberin başlığı: ekran okuyucu yirmi kez yalnızca "Kaydet" okumaz. */
  title?: string
  className?: string
}

/**
 * Yer imi düğmesi: kaydedilmemiş haberde boş, kaydedilmişte dolu yer imi. React Aria'nın aç/kapa
 * düğmesidir; durumu ekran okuyucuya `aria-pressed` ile bildirir ("Kaydet, basılı"). Adı durumla
 * değişmez (WAI-ARIA APG, Button pattern): "Kaydedildi, basılı" gibi çelişkili bir okuma olmaz.
 */
export function BookmarkToggle({ isSaved, onChange, isDisabled, title, className }: BookmarkToggleProps) {
  const { t } = useTranslation()

  return (
    <ToggleButton
      isSelected={isSaved}
      onChange={onChange}
      isDisabled={isDisabled}
      aria-label={title ? t('bookmark.saveWithTitle', { title }) : t('bookmark.save')}
      className={cn(buttonVariants({ variant: 'ghost', size: 'icon' }), 'text-muted-foreground', className)}
    >
      <BookmarkIcon aria-hidden className={cn('size-5', isSaved && 'fill-primary text-primary')} />
    </ToggleButton>
  )
}
