/*
 * Haber metninin yazı boyutu (A− / A+). Seçim tarayıcıda saklanır; bütün haberlerde geçerlidir ve sonraki
 * açılışta da aynı gelir. Tarayıcının kendi yazı büyütmesi (Ctrl +) de çalışmaya devam eder.
 */
import { useState } from 'react'

/** Küçükten büyüğe boyutlar (Tailwind sınıfları). `.article-body`'nin varsayılanı text-lg'dir. */
const SIZES = ['text-base', 'text-lg', 'text-xl', 'text-2xl'] as const
const DEFAULT_INDEX = 1
const STORAGE_KEY = 'articleTextSize'

/** Saklanan boyut; kayıt yoksa, bozuksa veya depolama engelliyse varsayılan boyut. */
function readStoredIndex(): number {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    // Number(null) 0 verirdi; kayıt yoksa geçersiz sayılır.
    const index = stored === null ? Number.NaN : Number(stored)
    return Number.isInteger(index) && index >= 0 && index < SIZES.length ? index : DEFAULT_INDEX
  } catch {
    return DEFAULT_INDEX
  }
}

/** Seçili boyutun sınıfı ve boyutu değiştiren fonksiyonlar. */
export function useArticleTextSize() {
  const [index, setIndex] = useState(readStoredIndex)

  const change = (next: number) => {
    setIndex(next)
    try {
      localStorage.setItem(STORAGE_KEY, String(next))
    } catch {
      // Depolama engelliyse boyut bu sayfada yine değişir; yalnızca sonraki açılışta hatırlanmaz.
    }
  }

  return {
    className: SIZES[index],
    canDecrease: index > 0,
    canIncrease: index < SIZES.length - 1,
    decrease: () => change(Math.max(0, index - 1)),
    increase: () => change(Math.min(SIZES.length - 1, index + 1)),
  }
}
