import { cn } from 'cn'
import { useTranslation } from 'react-i18next'
import type { SourceRef } from '../../api/articles'
import { initialsOf } from './initials'
import { BREAKING } from './useCategories'

/**
 * Son dakika etiketi: başlığın yanında küçük bordo bir etiket (tam genişlik bir bant yerine). Haber Son
 * Dakika kategorisini yalnızca 6 saat taşır (API süresi dolan kategoriyi göndermez); etiket de o süre görünür.
 */
export function BreakingBadge({ categories, className }: { categories: string[]; className?: string }) {
  const { t } = useTranslation()
  if (!categories.includes(BREAKING)) {
    return null
  }
  return (
    <span
      className={cn(
        'inline-block rounded-sm bg-primary px-1.5 py-0.5 text-[0.7rem] leading-none font-semibold tracking-wide text-primary-foreground uppercase',
        className,
      )}
    >
      {t(`categories.${BREAKING}`)}
    </span>
  )
}

/**
 * Kaynağın baş harfleri (TRT Haber → TH, NTV → NT). Logolar kaynak sitelerden çekilmez: her görüntülemede
 * kullanıcının adresi o sitelere gitmiş olurdu. Kaynağın adı hemen yanında yazdığı için ekran okuyucuya okunmaz.
 */
export function SourceBadge({ source, className }: { source: SourceRef; className?: string }) {
  return (
    <span
      aria-hidden
      className={cn(
        'inline-flex size-5 shrink-0 items-center justify-center rounded-sm bg-muted text-[0.6rem] font-semibold text-foreground',
        className,
      )}
    >
      {initialsOf(source.name)}
    </span>
  )
}
