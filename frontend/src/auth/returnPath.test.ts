import { describe, expect, it } from 'vitest'
import { safeReturnPath } from './returnPath'

describe('safeReturnPath', () => {
  it.each(['/', '/articles/0193f1a2', '/?q=deprem&page=2'])(
    'uygulamanın kendi yolunu olduğu gibi döner: %s',
    (path) => {
      expect(safeReturnPath(path)).toBe(path)
    },
  )

  it.each([
    ['başka bir site', 'https://kotu.site/'],
    ['şemasız başka site', '//kotu.site/yol'],
    ['ters eğik çizgiyle başka site', '/\\kotu.site'],
    ['göreli yol', 'articles/1'],
    ['girişten dönüş sayfası', '/oidc-callback?code=x'],
    ['metin olmayan değer', { returnTo: '/' }],
    ['değer yok', undefined],
  ])('güvenli olmayan değerde ana sayfaya döner: %s', (_case, value) => {
    expect(safeReturnPath(value)).toBe('/')
  })
})
