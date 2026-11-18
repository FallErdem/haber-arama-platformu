import { describe, expect, it } from 'vitest'
import { formatPublishedAt } from './time'

const NOW = new Date('2026-11-18T12:00:00Z')

describe('formatPublishedAt', () => {
  it.each([
    ['30 saniye önce', '2026-11-18T11:59:30Z', 'şimdi'],
    ['saatler arasındaki fark yüzünden gelecekte', '2026-11-18T12:00:20Z', 'şimdi'],
    ['5 dakika önce', '2026-11-18T11:55:00Z', '5 dakika önce'],
    ['3 saat önce', '2026-11-18T09:00:00Z', '3 saat önce'],
  ])('son 24 saatteki haberde göreli zaman gösterir: %s', (_case, iso, expected) => {
    expect(formatPublishedAt(iso, 'tr-TR', NOW)).toBe(expected)
  })

  it('daha eski haberde Türkiye saatiyle tarih ve saat gösterir', () => {
    // 08:12 UTC, Türkiye'de 11:12'dir.
    expect(formatPublishedAt('2026-11-05T08:12:00Z', 'tr-TR', NOW)).toBe('5 Kasım 2026 11:12')
  })

  it('tarihi seçilen dilde biçimlendirir', () => {
    expect(formatPublishedAt('2026-11-18T09:00:00Z', 'en-GB', NOW)).toBe('3 hours ago')
  })
})
