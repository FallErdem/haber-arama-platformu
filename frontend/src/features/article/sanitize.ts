import DOMPurify from 'dompurify'

/*
 * Haberin tam metni HTML'dir ve sayfaya HTML olarak basılır (paragraflar, bağlantılar, listeler).
 * İşçi metni kaydederken nh3 ile temizler (FOG-16); burada DOMPurify ile ikinci kez temizlenir.
 * İşçideki temizlik bir gün bir hata yüzünden atlanırsa sayfaya sızan bir betik bellekteki token'ı
 * okuyabilirdi; bu ikinci savunma hattıdır.
 *
 * İzin verilen etiket ve öznitelikler işçideki nh3 listesiyle aynıdır (nh3 0.3.7 ALLOWED_TAGS,
 * görseller hariç; bkz. worker/src/news_worker/html_cleaner.py). Listede olmayan her şey (script,
 * style, iframe, olay öznitelikleri, javascript: adresleri) atılır.
 */
const ALLOWED_TAGS = [
  'a', 'abbr', 'acronym', 'article', 'aside', 'b', 'bdi', 'bdo', 'blockquote', 'br', 'caption', 'center',
  'cite', 'code', 'col', 'colgroup', 'data', 'dd', 'del', 'details', 'dfn', 'div', 'dl', 'dt', 'em',
  'figcaption', 'figure', 'footer', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'header', 'hgroup', 'hr', 'i',
  'ins', 'kbd', 'li', 'mark', 'nav', 'ol', 'p', 'pre', 'q', 'rp', 'rt', 'rtc', 'ruby', 's', 'samp',
  'small', 'span', 'strike', 'strong', 'sub', 'summary', 'sup', 'table', 'tbody', 'td', 'th', 'thead',
  'time', 'tr', 'tt', 'u', 'ul', 'var', 'wbr',
] // prettier-ignore

const ALLOWED_ATTR = [
  'href', 'hreflang', 'cite', 'datetime', 'start', 'colspan', 'rowspan', 'headers', 'scope', 'span', 'dir',
] // prettier-ignore

// Metindeki bağlantılar yeni sekmede açılır; açılan sayfa bu sayfaya erişemez (noopener) ve hangi
// sayfadan gelindiğini öğrenemez (noreferrer). Ekran akışları 2. bölüm.
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A' && node.hasAttribute('href')) {
    node.setAttribute('target', '_blank')
    node.setAttribute('rel', 'noopener noreferrer')
  }
})

/** Haberin tam metnini sayfaya basmaya hazır, temizlenmiş HTML olarak döner. */
export function sanitizeContent(html: string): string {
  return DOMPurify.sanitize(html, { ALLOWED_TAGS, ALLOWED_ATTR, ADD_ATTR: ['target', 'rel'] })
}
