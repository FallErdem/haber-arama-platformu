import { describe, expect, it } from 'vitest'
import { sanitizeContent } from './sanitize'

describe('sanitizeContent', () => {
  it('paragrafları, vurguları ve listeleri olduğu gibi bırakır', () => {
    const html = '<p>Birinci <strong>önemli</strong> paragraf.</p><ul><li>Madde</li></ul>'

    expect(sanitizeContent(html)).toBe(html)
  })

  it('betikleri, stilleri, çerçeveleri ve görselleri atar', () => {
    const html =
      '<p>Metin</p><script>alert(1)</script><style>p{}</style><iframe src="https://x.test"></iframe><img src="x">'

    expect(sanitizeContent(html)).toBe('<p>Metin</p>')
  })

  it('olay özniteliklerini ve javascript: adreslerini atar', () => {
    const result = sanitizeContent('<p onclick="alert(1)">a</p><a href="javascript:alert(1)">b</a>')

    expect(result).not.toContain('onclick')
    expect(result).not.toContain('javascript:')
  })

  it('bağlantıları yeni sekmede, noopener ve noreferrer ile açar', () => {
    const result = sanitizeContent('<p><a href="https://example.test/kaynak">kaynak</a></p>')

    expect(result).toBe(
      '<p><a href="https://example.test/kaynak" target="_blank" rel="noopener noreferrer">kaynak</a></p>',
    )
  })

  it('listede olmayan öznitelikleri atar', () => {
    expect(sanitizeContent('<p class="x" style="color:red" id="y">a</p>')).toBe('<p>a</p>')
  })
})
