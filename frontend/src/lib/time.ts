import { parseDate } from '@internationalized/date'

/** Tarihler Türkiye saatiyle gösterilir ve seçilir (ekran akışları 2. bölüm); API'den UTC gelir. */
export const TIME_ZONE = 'Europe/Istanbul'

/** Takvimde var olan bir gün mü (`2026-11-05`); `2026-02-30` veya `05-11-2026` değildir. */
export function isIsoDay(value: string): boolean {
  try {
    return parseDate(value).toString() === value
  } catch {
    return false
  }
}

/** Türkiye saatinde günün ilk anı. Saat farkı sabit yazılmaz; saat dilimi kurallarından hesaplanır. */
export function startOfDay(day: string): Date {
  return parseDate(day).toDate(TIME_ZONE)
}

/** Türkiye saatinde günün son anı: ertesi günün ilk anından bir milisaniye önce. */
export function endOfDay(day: string): Date {
  return new Date(parseDate(day).add({ days: 1 }).toDate(TIME_ZONE).getTime() - 1)
}

const MINUTE = 60_000
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR

/**
 * Haberin yayın zamanı: son 24 saatte yayımlandıysa göreli ("5 dakika önce", "3 saat önce"), daha
 * eskiyse Türkiye saatiyle tarih ve saat ("5 Kasım 2026 14:30"). Biçimler dile göre tarayıcının
 * Intl kütüphanesinden gelir; metinler dil dosyasında tutulmaz.
 */
export function formatPublishedAt(iso: string, locale: string, now: Date = new Date()): string {
  const publishedAt = new Date(iso)
  const elapsed = now.getTime() - publishedAt.getTime()
  const relative = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' })

  // Bilgisayarların saatleri arasındaki küçük farklar yüzünden "gelecekteki" haber de "şimdi" sayılır.
  if (elapsed < MINUTE) return relative.format(0, 'second')
  if (elapsed < HOUR) return relative.format(-Math.floor(elapsed / MINUTE), 'minute')
  if (elapsed < DAY) return relative.format(-Math.floor(elapsed / HOUR), 'hour')

  return formatDateTime(iso, locale)
}

/** Türkiye saatiyle tarih ve saat: "5 Kasım 2026 11:12". Haber detayında her zaman bu biçim kullanılır. */
export function formatDateTime(iso: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: TIME_ZONE,
  }).format(new Date(iso))
}
