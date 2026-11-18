/*
 * shadcn/ui düğmesi (stil: aria-nova, shadcn 4.23.0). shadcn bileşenleri bir paket olarak kurulmaz;
 * kaynak kodu projeye kopyalanır ve projenin parçası olur. Altta React Aria'nın Button bileşeni
 * çalışır: klavye, dokunma ve ekran okuyucu davranışını o sağlar (FOG-30).
 */
import type * as React from 'react'
import type { VariantProps } from 'class-variance-authority'
import { cn } from 'cn'
import {
  Button as ButtonPrimitive,
  Link as LinkPrimitive,
  type ButtonProps as ButtonPrimitiveProps,
  type LinkProps as LinkPrimitiveProps,
} from 'react-aria-components'
import { buttonVariants } from './button-variants'

/**
 * Düğme. React Aria'da tıklama olayı `onClick` değil `onPress`'tir: fare, dokunma ve klavye
 * (Enter, Boşluk) aynı olayla gelir.
 */
function Button({
  className,
  variant = 'default',
  size = 'default',
  ...props
}: Omit<ButtonPrimitiveProps, 'className'> &
  React.RefAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & {
    className?: string
  }) {
  return (
    <ButtonPrimitive
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

/** Düğme görünümünde bağlantı. */
function LinkButton({
  className,
  variant = 'default',
  size = 'default',
  ...props
}: Omit<LinkPrimitiveProps, 'className'> &
  VariantProps<typeof buttonVariants> & {
    className?: string
  }) {
  return (
    <LinkPrimitive
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, LinkButton }
