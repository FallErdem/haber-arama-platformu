/*
 * shadcn/ui açılır pencere (stil: aria-nova, shadcn 4.23.0); yalnızca pencerenin kendisi alındı.
 * Bir düğmeyle birlikte React Aria'nın DialogTrigger'ı içinde kullanılır. Odak pencereye taşınır,
 * Escape ile ya da dışına tıklayınca kapanır ve odak açan düğmeye geri döner.
 */
import { cn } from 'cn'
import { Popover as PopoverPrimitive, type PopoverProps } from 'react-aria-components'

function Popover({
  className,
  placement = 'bottom start',
  offset = 4,
  ...props
}: Omit<PopoverProps, 'className'> & { className?: string }) {
  return (
    <PopoverPrimitive
      data-slot="popover-content"
      placement={placement}
      offset={offset}
      className={cn(
        'z-50 flex origin-(--trigger-anchor-point) flex-col gap-2.5 rounded-lg bg-popover p-2.5 text-sm text-popover-foreground shadow-md ring-1 ring-foreground/10 outline-hidden duration-100 data-entering:animate-in data-entering:fade-in-0 data-entering:zoom-in-95 data-exiting:animate-out data-exiting:fade-out-0 data-exiting:zoom-out-95',
        className,
      )}
      {...props}
    />
  )
}

export { Popover }
