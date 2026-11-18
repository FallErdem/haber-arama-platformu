/** Tarihler Türkiye saatiyle gösterilir ve seçilir (ekran akışları 2. bölüm); API'den UTC gelir. */
export const TIME_ZONE = 'Europe/Istanbul'

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
