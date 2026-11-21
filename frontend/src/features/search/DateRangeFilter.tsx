import { DateFormatter, parseDate, today } from '@internationalized/date'
import { cn } from 'cn'
import { CalendarIcon } from 'lucide-react'
import { Dialog, DialogTrigger, useLocale } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { Button } from '../../components/ui/button'
import { RangeCalendar } from '../../components/ui/calendar'
import { Popover } from '../../components/ui/popover'
import { TIME_ZONE } from '../../lib/time'

interface DateRangeFilterProps {
  /** Aralığın günleri (`2026-11-05`), Türkiye saatiyle; iki uç da dahil. */
  from: string | undefined
  to: string | undefined
  onChange: (from: string | undefined, to: string | undefined) => void
  /** Tarih seçilmemişken düğmenin metni; verilmezse "Tarih". */
  emptyLabel?: string
}

/**
 * Yayın tarihi aralığı filtresi: düğmeye basınca takvim açılır, önce başlangıç sonra bitiş günü
 * seçilir ve pencere kapanır. Gelecekteki günler seçilemez. Ay adları ve haftanın ilk günü dil
 * ayarından gelir (Türkçede Pazartesi).
 */
export function DateRangeFilter({ from, to, onChange, emptyLabel }: DateRangeFilterProps) {
  const { t } = useTranslation()
  const { locale } = useLocale()
  const value = from && to ? { start: parseDate(from), end: parseDate(to) } : null
  const label = from || to ? formatRange(locale, from, to) : (emptyLabel ?? t('search.filters.date'))

  return (
    <DialogTrigger>
      <Button variant="outline" className={cn(value && 'border-primary text-primary')}>
        <CalendarIcon aria-hidden />
        {label}
      </Button>
      <Popover>
        <Dialog aria-label={t('search.filters.date')} className="flex flex-col gap-2 outline-none">
          {({ close }) => (
            <>
              <RangeCalendar
                value={value}
                maxValue={today(TIME_ZONE)}
                onChange={(range) => {
                  onChange(range.start.toString(), range.end.toString())
                  close()
                }}
              />
              {(from || to) && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="self-end"
                  onPress={() => {
                    onChange(undefined, undefined)
                    close()
                  }}
                >
                  {t('search.filters.clearDate')}
                </Button>
              )}
            </>
          )}
        </Dialog>
      </Popover>
    </DialogTrigger>
  )
}

/** "5–18 Kas" gibi kısa bir aralık; yıl bu yıldan farklıysa yazılır. Biçim dile göre Intl'den gelir. */
function formatRange(locale: string, from: string | undefined, to: string | undefined): string {
  const thisYear = today(TIME_ZONE).year
  const days = [from, to].filter((day) => day !== undefined).map((day) => parseDate(day))
  const showYear = days.some((day) => day.year !== thisYear)
  const formatter = new DateFormatter(locale, {
    day: 'numeric',
    month: 'short',
    year: showYear ? 'numeric' : undefined,
    timeZone: TIME_ZONE,
  })
  const start = from ? parseDate(from).toDate(TIME_ZONE) : undefined
  const end = to ? parseDate(to).toDate(TIME_ZONE) : undefined
  if (start && end) return formatter.formatRange(start, end)
  // Adreste yalnızca bir uç varsa (elle yazılmış adres) o uç gösterilir.
  return start ? `${formatter.format(start)} –` : `– ${formatter.format(end!)}`
}
