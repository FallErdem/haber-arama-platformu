/*
 * shadcn/ui takvimi (stil: aria-nova, shadcn 4.23.0); yalnızca aralık takvimi alındı. Altta React
 * Aria'nın RangeCalendar bileşeni çalışır: günler arasında oklarla gezinme, Enter ile aralığın başı
 * ve sonunu seçme, ay adları ve haftanın ilk günü dil ayarından (I18nProvider) gelir.
 */
import { cn } from 'cn'
import { ChevronLeftIcon, ChevronRightIcon } from 'lucide-react'
import {
  CalendarCell,
  CalendarGrid,
  CalendarGridBody,
  CalendarGridHeader,
  CalendarHeaderCell,
  Heading,
  RangeCalendar as AriaRangeCalendar,
  type DateValue,
  type RangeCalendarProps,
} from 'react-aria-components'
import { Button } from './button'
import { buttonVariants } from './button-variants'

function RangeCalendar<T extends DateValue>({
  className,
  ...props
}: Omit<RangeCalendarProps<T>, 'className'> & { className?: string }) {
  return (
    <AriaRangeCalendar
      data-slot="calendar"
      className={cn('w-fit p-1 [--cell-radius:var(--radius-md)] [--cell-size:--spacing(8)]', className)}
      {...props}
    >
      <header className="flex items-center justify-between gap-1 pb-2">
        {/* slot="previous"/"next": React Aria bu düğmeleri önceki/sonraki aya geçiş düğmesi olarak bağlar. */}
        <Button variant="ghost" size="icon" slot="previous" className="size-(--cell-size)">
          <ChevronLeftIcon aria-hidden className="size-4" />
        </Button>
        <Heading className="text-sm font-medium select-none" />
        <Button variant="ghost" size="icon" slot="next" className="size-(--cell-size)">
          <ChevronRightIcon aria-hidden className="size-4" />
        </Button>
      </header>
      <CalendarGrid className="border-collapse">
        <CalendarGridHeader>
          {(day) => (
            <CalendarHeaderCell className="pb-1 text-[0.8rem] font-normal text-muted-foreground select-none">
              {day}
            </CalendarHeaderCell>
          )}
        </CalendarGridHeader>
        <CalendarGridBody>
          {(date) => (
            <CalendarCell
              date={date}
              className={({ isSelected, isSelectionStart, isSelectionEnd, isOutsideMonth, isDisabled }) =>
                cn(
                  buttonVariants({ variant: 'ghost', size: 'icon' }),
                  'size-(--cell-size) rounded-none font-normal tabular-nums outline-none',
                  'data-focus-visible:z-10 data-focus-visible:ring-3 data-focus-visible:ring-ring/50',
                  // Aralığın içi soluk, başı ve sonu vurgu rengiyle gösterilir.
                  isSelected && 'bg-muted',
                  (isSelectionStart || isSelectionEnd) && 'bg-primary text-primary-foreground hover:bg-primary/90',
                  isSelectionStart && 'rounded-l-(--cell-radius)',
                  isSelectionEnd && 'rounded-r-(--cell-radius)',
                  !isSelected && 'rounded-(--cell-radius)',
                  isOutsideMonth && 'text-muted-foreground opacity-50',
                  isDisabled && 'pointer-events-none opacity-30',
                )
              }
            />
          )}
        </CalendarGridBody>
      </CalendarGrid>
    </AriaRangeCalendar>
  )
}

export { RangeCalendar }
