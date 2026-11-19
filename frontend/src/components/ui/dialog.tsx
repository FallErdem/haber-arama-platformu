/*
 * shadcn/ui pencere (stil: aria-nova, shadcn 4.23.0); yalnızca kullanılan parçalar alındı. Sağ üstteki
 * kapatma düğmesi alınmadı: penceredeki "Vazgeç" düğmesi ve Escape tuşu aynı işi görür.
 *
 * Altta React Aria'nın ModalOverlay, Modal ve Dialog bileşenleri çalışır: pencere açılınca odak
 * pencereye taşınır ve pencerenin içinde kalır (Tab dışarı çıkmaz), Escape veya dışarı tıklama kapatır,
 * kapanınca odak pencereyi açan düğmeye döner; ekran okuyucu pencereyi başlığıyla duyurur (FOG-30).
 *
 * Kullanım (açık olup olmadığını çağıran tutar):
 *   <Dialog isOpen={open} onOpenChange={setOpen}>
 *     <DialogHeader><DialogTitle>Başlık</DialogTitle><DialogDescription>Açıklama</DialogDescription></DialogHeader>
 *     <DialogFooter><DialogClose>Vazgeç</DialogClose><Button>Onayla</Button></DialogFooter>
 *   </Dialog>
 */
import type * as React from 'react'
import { cn } from 'cn'
import {
  Dialog as DialogPrimitive,
  Heading,
  ModalOverlay as ModalOverlayPrimitive,
  Modal as ModalPrimitive,
  type ModalOverlayProps as ModalOverlayPrimitiveProps,
} from 'react-aria-components'
import { Button } from './button'

/** Pencereyi kapatan düğme: React Aria `slot="close"` ile içinde bulunduğu pencereyi kapatır. */
function DialogClose({
  className,
  variant = 'outline',
  size = 'default',
  ...props
}: React.ComponentProps<typeof Button>) {
  return (
    <Button slot="close" data-slot="dialog-close" variant={variant} size={size} className={cn(className)} {...props} />
  )
}

function Dialog({
  className,
  children,
  isDismissable = true,
  ...props
}: Omit<ModalOverlayPrimitiveProps, 'className' | 'children'> &
  Pick<React.ComponentProps<typeof ModalPrimitive>, 'isDismissable'> & {
    className?: string
    children: React.ReactNode
  }) {
  return (
    <ModalOverlayPrimitive
      data-slot="dialog-overlay"
      isDismissable={isDismissable}
      className="fixed inset-0 isolate z-50 bg-black/10 duration-100 data-entering:animate-in data-entering:fade-in-0 data-exiting:animate-out data-exiting:fade-out-0 supports-backdrop-filter:backdrop-blur-xs"
      {...props}
    >
      <ModalPrimitive
        data-slot="dialog-content"
        className={cn(
          'fixed top-1/2 left-1/2 z-50 grid w-full max-w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2 gap-4 rounded-xl bg-popover p-4 text-sm text-popover-foreground ring-1 ring-foreground/10 duration-100 outline-none data-entering:animate-in data-entering:fade-in-0 data-entering:zoom-in-95 data-exiting:animate-out data-exiting:fade-out-0 data-exiting:zoom-out-95 sm:max-w-sm',
          className,
        )}
      >
        <DialogPrimitive data-slot="dialog" className="[display:inherit] [gap:inherit] outline-none">
          {children}
        </DialogPrimitive>
      </ModalPrimitive>
    </ModalOverlayPrimitive>
  )
}

function DialogHeader({ className, ...props }: React.ComponentProps<'div'>) {
  return <div data-slot="dialog-header" className={cn('flex flex-col gap-2', className)} {...props} />
}

function DialogFooter({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="dialog-footer"
      className={cn(
        '-mx-4 -mb-4 flex flex-col-reverse gap-2 rounded-b-xl border-t bg-muted/50 p-4 sm:flex-row sm:justify-end',
        className,
      )}
      {...props}
    />
  )
}

/** Pencerenin başlığı; React Aria pencereyi bu başlıkla adlandırır (`aria-labelledby`). */
function DialogTitle({ className, ...props }: Omit<React.ComponentProps<typeof Heading>, 'slot'>) {
  return (
    <Heading
      slot="title"
      data-slot="dialog-title"
      className={cn('font-heading text-base leading-none font-medium', className)}
      {...props}
    />
  )
}

function DialogDescription({ className, ...props }: Omit<React.ComponentProps<'div'>, 'slot'>) {
  return <div data-slot="dialog-description" className={cn('text-sm text-muted-foreground', className)} {...props} />
}

export { Dialog, DialogClose, DialogDescription, DialogFooter, DialogHeader, DialogTitle }
