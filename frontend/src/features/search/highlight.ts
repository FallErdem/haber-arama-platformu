/** Vurgulanmış metnin bir parçası: eşleşen kelime(ler) veya aradaki metin. */
export interface HighlightPart {
  text: string
  isMatch: boolean
}

const MARK = /(<mark>[\s\S]*?<\/mark>)/

/**
 * API'nin vurgusunu parçalara ayırır (API sözleşmesi 4.1). Vurguda yalnızca `<mark>` etiketi vardır;
 * metnin geri kalanı Elasticsearch tarafından HTML kaçış kodlarına çevrilmiştir (`&amp;`, `&lt;`).
 *
 * Sonuç sayfaya HTML olarak basılmaz (innerHTML yok): her parça React'e düz metin olarak verilir,
 * eşleşen parçalar `<mark>` öğesine sarılır. Böylece haber metninde bir etiket olsa bile sayfaya
 * sızamaz; arayüz `<mark>` dışında hiçbir etiketi işlemez.
 */
export function parseHighlight(fragment: string): HighlightPart[] {
  return fragment
    .split(MARK)
    .filter((part) => part !== '')
    .map((part) => {
      const isMatch = part.startsWith('<mark>') && part.endsWith('</mark>')
      const text = isMatch ? part.slice('<mark>'.length, -'</mark>'.length) : part
      return { text: decodeEntities(text), isMatch }
    })
}

/**
 * HTML kaçış kodlarını çözer (`&amp;` → `&`). DOMParser'ın ürettiği belge sayfaya eklenmez ve
 * içindeki hiçbir şey çalıştırılmaz; yalnızca metni okunur.
 *
 * Metin açıkça `<body>` içine konur: HTML kurallarına göre belgenin başındaki boşluklar atılır,
 * `<body>`'nin içindekiler ise korunur. Aksi halde "Deprem sonrası" "Depremsonrası" olurdu.
 */
function decodeEntities(text: string): string {
  return new DOMParser().parseFromString(`<!doctype html><body>${text}`, 'text/html').body.textContent
}
