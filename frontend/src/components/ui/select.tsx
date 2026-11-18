/*
 * shadcn/ui seçim kutusu (stil: aria-nova, shadcn 4.23.0); yalnızca kullanılan parçalar alındı.
 * Altta React Aria'nın Select bileşeni çalışır: açılır liste, klavyeyle gezinme (oklar, yazarak
 * arama), ekran okuyucu duyuruları ve çoklu seçim (`selectionMode="multiple"`) ondan gelir.
 *
 * Kullanım:
 *   <Select aria-label="Kaynak" selectionMode="multiple" value={kodlar} onChange={...}>
 *     <SelectTrigger><SelectValue /></SelectTrigger>
 *     <SelectContent><SelectItem id="TRT">TRT Haber</SelectItem></SelectContent>
 *   </Select>
 */
import type * as React from 'react'
import { cn } from 'cn'
import { CheckIcon, ChevronDownIcon } from 'lucide-react'
import {
  Button as ButtonPrimitive,
  composeRenderProps,
  ListBox as ListBoxPrimitive,
  ListBoxItem as ListBoxItemPrimitive,
  Popover as PopoverPrimitive,
  Select as SelectPrimitive,
  SelectValue as SelectValuePrimitive,
  type SelectProps,
  type SelectValueProps,
} from 'react-aria-components'

function Select<T extends object, M extends 'single' | 'multiple' = 'single'>({
  className,
  ...props
}: Omit<SelectProps<T, M>, 'className'> & { className?: string }) {
  return <SelectPrimitive data-slot="select" className={cn('w-fit', className)} {...props} />
}

/** Seçili değerin metni. Seçim yoksa `placeholder` soluk renkle gösterilir. */
function SelectValue<T extends object>({ className, ...props }: SelectValueProps<T>) {
  return (
    <SelectValuePrimitive
      data-slot="select-value"
      className={cn('flex flex-1 text-left data-placeholder:text-muted-foreground', className)}
      {...props}
    />
  )
}

/** Listeyi açan düğme. */
function SelectTrigger({
  className,
  children,
  ...props
}: Omit<React.ComponentProps<typeof ButtonPrimitive>, 'children' | 'className'> & {
  className?: string
  children?: React.ReactNode
}) {
  return (
    <ButtonPrimitive
      data-slot="select-trigger"
      className={cn(
        "flex h-8 w-full items-center justify-between gap-1.5 rounded-lg border border-input bg-transparent py-2 pr-2 pl-2.5 text-sm whitespace-nowrap transition-colors outline-none select-none hover:bg-muted focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 *:data-[slot=select-value]:line-clamp-1 *:data-[slot=select-value]:flex *:data-[slot=select-value]:items-center *:data-[slot=select-value]:gap-1.5 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        className,
      )}
      {...props}
    >
      {children}
      <ChevronDownIcon aria-hidden className="pointer-events-none size-4 text-muted-foreground" />
    </ButtonPrimitive>
  )
}

/** Açılan liste: düğmenin altında, en az düğme genişliğinde bir pencere içinde. */
function SelectContent({ className, children }: { className?: string; children?: React.ReactNode }) {
  return (
    <PopoverPrimitive
      data-slot="select-content"
      placement="bottom start"
      offset={4}
      className={cn(
        'relative isolate z-50 max-h-80 min-w-(--trigger-width) origin-(--trigger-anchor-point) overflow-hidden rounded-lg bg-popover text-popover-foreground shadow-md ring-1 ring-foreground/10 duration-100 data-entering:animate-in data-entering:fade-in-0 data-entering:zoom-in-95 data-exiting:animate-out data-exiting:fade-out-0 data-exiting:zoom-out-95',
        className,
      )}
    >
      <ListBoxPrimitive
        data-slot="select-list"
        className="max-h-[inherit] overflow-x-hidden overflow-y-auto p-1 outline-hidden"
      >
        {children}
      </ListBoxPrimitive>
    </PopoverPrimitive>
  )
}

/** Listedeki bir seçenek; seçiliyse sağında onay işareti görünür. */
function SelectItem({
  className,
  children,
  ...props
}: Omit<React.ComponentProps<typeof ListBoxItemPrimitive>, 'className'> & { className?: string }) {
  return (
    <ListBoxItemPrimitive
      data-slot="select-item"
      // Seçeneğin düz metni: klavyeyle yazarak aramada ve ekran okuyucuda kullanılır.
      textValue={typeof children === 'string' ? children : undefined}
      className={cn(
        'relative flex w-full cursor-default items-center gap-1.5 rounded-md py-1.5 pr-8 pl-2 text-sm outline-hidden select-none data-disabled:pointer-events-none data-disabled:opacity-50 data-focused:bg-accent data-focused:text-accent-foreground',
        className,
      )}
      {...props}
    >
      {composeRenderProps(children, (children, { isSelected }) => (
        <>
          <span className="flex flex-1 shrink-0 gap-2 whitespace-nowrap">{children}</span>
          <span className="pointer-events-none absolute right-2 flex size-4 items-center justify-center">
            {isSelected ? <CheckIcon aria-hidden className="size-4 text-primary" /> : null}
          </span>
        </>
      ))}
    </ListBoxItemPrimitive>
  )
}

export { Select, SelectContent, SelectItem, SelectTrigger, SelectValue }
