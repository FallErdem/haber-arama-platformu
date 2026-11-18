/*
 * shadcn/ui metin kutusu (stil: aria-nova, shadcn 4.23.0). React Aria'nın Input bileşenidir; bir
 * TextField veya SearchField içinde kullanıldığında etiketi ve hata metniyle kendiliğinden bağlanır.
 */
import type * as React from 'react'
import { cn } from 'cn'
import { composeRenderProps, Input as InputPrimitive } from 'react-aria-components'

function Input({ className, ...props }: React.ComponentProps<typeof InputPrimitive>) {
  return (
    <InputPrimitive
      data-slot="input"
      className={composeRenderProps(className, (className) =>
        cn(
          'h-8 w-full min-w-0 rounded-lg border border-input bg-transparent px-2.5 py-1 text-base transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm',
          className,
        ),
      )}
      {...props}
    />
  )
}

export { Input }
