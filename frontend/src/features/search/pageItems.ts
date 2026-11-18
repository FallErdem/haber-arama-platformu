/** Sayfalamada bir yuva: sayfa numarası ya da atlanan sayfaların yerine "…". */
export type PageItem = number | 'gap'

/** Gösterilen yuva sayısı: ilk ve son sayfa, bulunulan sayfa ve iki komşusu, iki "…". */
const SLOTS = 7

/**
 * Sayfalamada gösterilecek numaralar. Yuva sayısı her sayfada aynıdır (7); böylece sayfa değişince
 * bağlantılar kaymaz ve "Sonraki" düğmesi aynı yerde kalır.
 *
 *   pageItems(2, 150)   → 1 2 3 4 5 … 150
 *   pageItems(75, 150)  → 1 … 74 75 76 … 150
 *   pageItems(149, 150) → 1 … 146 147 148 149 150
 */
export function pageItems(page: number, lastPage: number): PageItem[] {
  if (lastPage <= SLOTS) {
    return range(1, lastPage)
  }
  // Baştaki sayfalarda sağdaki "…"tan önce beş numara gösterilir; sondakilerde soldakinden sonra.
  if (page <= 4) {
    return [...range(1, 5), 'gap', lastPage]
  }
  if (page >= lastPage - 3) {
    return [1, 'gap', ...range(lastPage - 4, lastPage)]
  }
  return [1, 'gap', page - 1, page, page + 1, 'gap', lastPage]
}

function range(from: number, to: number): number[] {
  return Array.from({ length: to - from + 1 }, (_, index) => from + index)
}
