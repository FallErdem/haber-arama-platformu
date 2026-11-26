import { describe, expect, it } from 'vitest'
import { readingMinutes } from './readingTime'

const words = (count: number) => Array.from({ length: count }, () => 'kelime').join(' ')

describe('readingMinutes', () => {
  it('dakikada 200 kelimeyle hesaplar ve en yakın dakikaya yuvarlar', () => {
    expect(readingMinutes(`<p>${words(800)}</p>`)).toBe(4)
    expect(readingMinutes(`<p>${words(700)}</p>`)).toBe(4)
    expect(readingMinutes(`<p>${words(650)}</p>`)).toBe(3)
  })

  it('kısa metinde en az 1 dakika verir', () => {
    expect(readingMinutes('<p>Kısa bir haber.</p>')).toBe(1)
  })

  it('etiketleri saymaz, yalnızca okunan metni sayar', () => {
    const html = `<h2>Başlık</h2><p><a href="https://example.com">${words(199)}</a></p>`
    // 200 kelime: "Başlık" + 199 kelime; etiketler ve adres kelime sayılmaz.
    expect(readingMinutes(html)).toBe(1)
  })
})
