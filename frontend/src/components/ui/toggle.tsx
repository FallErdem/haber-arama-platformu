/*
 * shadcn/ui aç/kapa düğmesi (stil: aria-nova, shadcn 4.23.0). Altta React Aria'nın ToggleButton
 * bileşeni çalışır; düğmenin basılı olup olmadığını ekran okuyucuya `aria-pressed` ile bildirir.
 * Basılıyken vurgu renginde görünür.
 */
import { cn } from 'cn'
import { ToggleButton as TogglePrimitive, type ToggleButtonProps } from 'react-aria-components'

function Toggle({ className, ...props }: Omit<ToggleButtonProps, 'className'> & { className?: string }) {
  return (
    <TogglePrimitive
      data-slot="toggle"
      className={cn(
        "inline-flex h-8 min-w-8 items-center justify-center gap-1.5 rounded-lg border border-input bg-transparent px-2.5 text-sm font-medium whitespace-nowrap transition-colors outline-none hover:bg-muted focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50 data-selected:border-primary data-selected:bg-primary data-selected:text-primary-foreground data-selected:hover:bg-primary/90 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        className,
      )}
      {...props}
    />
  )
}

export { Toggle }
