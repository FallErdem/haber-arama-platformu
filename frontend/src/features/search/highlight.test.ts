import { describe, expect, it } from 'vitest'
import { parseHighlight } from './highlight'

describe('parseHighlight', () => {
  it('eşleşen kelimeleri ayırır', () => {
    expect(parseHighlight('<mark>Deprem</mark> sonrası <mark>son</mark> durum')).toEqual([
      { text: 'Deprem', isMatch: true },
      { text: ' sonrası ', isMatch: false },
      { text: 'son', isMatch: true },
      { text: ' durum', isMatch: false },
    ])
  })

  it('vurgusuz metni tek parça olarak döner', () => {
    expect(parseHighlight('Seçim takvimi açıklandı')).toEqual([{ text: 'Seçim takvimi açıklandı', isMatch: false }])
  })

  it('HTML kaçış kodlarını çözer', () => {
    expect(parseHighlight('Ar &amp; Ge &quot;<mark>yatırım</mark>&quot; &#39;planı&#39;')).toEqual([
      { text: 'Ar & Ge "', isMatch: false },
      { text: 'yatırım', isMatch: true },
      { text: "\" 'planı'", isMatch: false },
    ])
  })

  it('kaçış koduyla gelen etiketi metin olarak bırakır, öğeye dönüştürmez', () => {
    const parts = parseHighlight('&lt;script&gt;alert(1)&lt;/script&gt; <mark>haber</mark>')

    expect(parts[0]).toEqual({ text: '<script>alert(1)</script> ', isMatch: false })
    expect(parts[1]).toEqual({ text: 'haber', isMatch: true })
  })
})
