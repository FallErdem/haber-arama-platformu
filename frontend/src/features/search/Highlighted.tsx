import { parseHighlight } from './highlight'

/**
 * Vurgulanmış metni gösterir: eşleşen kelimeler `<mark>` içinde, gerisi düz metin.
 *
 * Aradaki metin bir öğeye (`<span>`) sarılmaz, düz metin olarak verilir: bazı erişilebilirlik
 * araçları her öğenin metnini ayrı ayrı kırptığı için `<span> sonrası</span>` baştaki boşluğunu
 * kaybeder ve bağlantının adı "Depremsonrası" olarak okunur.
 */
export function Highlighted({ fragment }: { fragment: string }) {
  return (
    <>
      {parseHighlight(fragment).map((part, index) => (part.isMatch ? <mark key={index}>{part.text}</mark> : part.text))}
    </>
  )
}
