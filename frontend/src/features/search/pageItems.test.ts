import { describe, expect, it } from 'vitest'
import { pageItems } from './pageItems'

describe('pageItems', () => {
  it('yedi veya daha az sayfada hepsini gösterir', () => {
    expect(pageItems(1, 1)).toEqual([1])
    expect(pageItems(3, 7)).toEqual([1, 2, 3, 4, 5, 6, 7])
  })

  it.each([1, 2, 3, 4])('baştaki sayfalarda ilk beş sayfayı ve son sayfayı gösterir: %i', (page) => {
    expect(pageItems(page, 150)).toEqual([1, 2, 3, 4, 5, 'gap', 150])
  })

  it('ortadaki sayfada bulunulan sayfayı komşularıyla, ilk ve son sayfayı gösterir', () => {
    expect(pageItems(75, 150)).toEqual([1, 'gap', 74, 75, 76, 'gap', 150])
    expect(pageItems(5, 150)).toEqual([1, 'gap', 4, 5, 6, 'gap', 150])
  })

  it.each([147, 148, 149, 150])('sondaki sayfalarda ilk sayfayı ve son beş sayfayı gösterir: %i', (page) => {
    expect(pageItems(page, 150)).toEqual([1, 'gap', 146, 147, 148, 149, 150])
  })

  it('her sayfada aynı sayıda yuva vardır; bağlantılar kaymaz', () => {
    const lengths = new Set(Array.from({ length: 150 }, (_, index) => pageItems(index + 1, 150).length))

    expect([...lengths]).toEqual([7])
  })
})
