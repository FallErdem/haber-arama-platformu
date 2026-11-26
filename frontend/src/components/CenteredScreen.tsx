import type { ReactNode } from 'react'
import { Logo } from './Logo'

/**
 * Uygulamaya girmeden önceki ekranların (yükleniyor, giriş, hesap durumu) ortak yerleşimi: içerik
 * sayfanın ortasında, dar bir sütunda; en üstte logo (üst çubuktakinin büyüğü).
 */
export function CenteredScreen({ children }: { children: ReactNode }) {
  return (
    <main className="flex min-h-dvh items-center justify-center px-4">
      <div className="w-full max-w-sm text-center">
        <Logo className="mx-auto mb-5 size-16" />
        {children}
      </div>
    </main>
  )
}
