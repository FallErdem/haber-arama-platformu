import type { ReactNode } from 'react'

/**
 * Uygulamaya girmeden önceki ekranların (yükleniyor, giriş, hesap durumu) ortak yerleşimi: içerik
 * sayfanın ortasında, dar bir sütunda.
 */
export function CenteredScreen({ children }: { children: ReactNode }) {
  return (
    <main className="flex min-h-dvh items-center justify-center px-4">
      <div className="w-full max-w-sm text-center">{children}</div>
    </main>
  )
}
