/** Okuma süresi kaba bir tahmindir: dakikada 200 kelime okunduğu varsayılır. */
const WORDS_PER_MINUTE = 200

/**
 * Haber metninin (temizlenmiş HTML) tahmini okuma süresi, dakika; en az 1. Etiketler sayılmaz, yalnızca
 * okunan metin sayılır. DOMParser metni çözümler ama içindeki betikleri çalıştırmaz.
 */
export function readingMinutes(html: string): number {
  const text = new DOMParser().parseFromString(html, 'text/html').body.textContent ?? ''
  const words = text.split(/\s+/).filter(Boolean).length
  return Math.max(1, Math.round(words / WORDS_PER_MINUTE))
}
