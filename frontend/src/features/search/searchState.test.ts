import { describe, expect, it } from 'vitest'
import { EMPTY_SEARCH, parseSearchState, toApiParams, toUrlParams, type SearchState } from './searchState'

function parse(query: string): SearchState {
  return parseSearchState(new URLSearchParams(query))
}

describe('parseSearchState', () => {
  it('parametresiz adreste boş aramayı döner', () => {
    expect(parse('')).toEqual(EMPTY_SEARCH)
  })

  it('bütün parametreleri okur', () => {
    expect(
      parse(
        'q=deprem&sources=TRT,NTV&language=tr&categories=GENERAL,BREAKING&from=2026-11-01&to=2026-11-18&sort=newest&page=3',
      ),
    ).toEqual({
      q: 'deprem',
      sources: ['TRT', 'NTV'],
      language: 'tr',
      categories: ['GENERAL', 'BREAKING'],
      from: '2026-11-01',
      to: '2026-11-18',
      sort: 'newest',
      page: 3,
    })
  })

  it.each([
    ['sayı olmayan', 'abc'],
    ['sıfır', '0'],
    ['negatif', '-2'],
    ['ondalıklı', '2.5'],
    ['10.000 sonuç sınırının ötesinde', '501'],
  ])('%s sayfa numarasında ilk sayfaya döner', (_case, page) => {
    expect(parse(`page=${page}`).page).toBe(1)
  })

  it("son izin verilen sayfa 500'dür (20 × 500 = 10.000 sonuç)", () => {
    expect(parse('page=500').page).toBe(500)
  })

  it('tanınmayan dil ve sıralamayı yok sayar', () => {
    const state = parse('language=de&sort=popular')

    expect(state.language).toBeUndefined()
    expect(state.sort).toBeUndefined()
  })

  it.each(['2026-02-30', '2026-13-01', '05-11-2026', '2026-11-5', 'dün'])(
    'takvimde olmayan tarihi yok sayar: %s',
    (day) => {
      expect(parse(`from=${day}`).from).toBeUndefined()
    },
  )

  it('başlangıcı bitişinden sonra olan aralığı yok sayar', () => {
    const state = parse('from=2026-11-10&to=2026-11-01')

    expect(state.from).toBeUndefined()
    expect(state.to).toBeUndefined()
  })

  it('tek günlük aralığı kabul eder', () => {
    expect(parse('from=2026-11-05&to=2026-11-05')).toMatchObject({ from: '2026-11-05', to: '2026-11-05' })
  })

  it('kod biçimine uymayan kaynakları ve tekrarları atar', () => {
    expect(parse('sources=TRT, NTV,,trt,TRT,<script>').sources).toEqual(['TRT', 'NTV'])
  })

  it('arama ifadesinin baştaki ve sondaki boşluklarını atar, 200 karakterden uzununu kısaltır', () => {
    expect(parse('q=%20%20deprem%20').q).toBe('deprem')
    expect(parse(`q=${'a'.repeat(250)}`).q).toHaveLength(200)
  })
})

describe('toUrlParams', () => {
  it('varsayılan değerleri adrese yazmaz', () => {
    expect(toUrlParams(EMPTY_SEARCH).toString()).toBe('')
    expect(toUrlParams({ ...EMPTY_SEARCH, q: 'deprem', page: 1 }).toString()).toBe('q=deprem')
  })

  it('okunan durumu aynı adrese geri çevirir', () => {
    const query =
      'q=deprem&sources=TRT%2CNTV&language=tr&categories=GENERAL&from=2026-11-01&to=2026-11-18&sort=newest&page=2'

    expect(toUrlParams(parse(query)).toString()).toBe(query)
  })
})

describe('toApiParams', () => {
  it("sayfayı 0'dan başlatır ve sayfa boyutunu ekler", () => {
    const params = toApiParams({ ...EMPTY_SEARCH, page: 2 })

    expect(params.get('page')).toBe('1')
    expect(params.get('size')).toBe('20')
  })

  it('tarih aralığını Türkiye saatindeki günlerin UTC başlangıç ve bitiş anlarına çevirir', () => {
    const params = toApiParams({ ...EMPTY_SEARCH, from: '2026-11-05', to: '2026-11-05' })

    expect(params.get('from')).toBe('2026-11-04T21:00:00.000Z')
    expect(params.get('to')).toBe('2026-11-05T20:59:59.999Z')
  })

  it('arama ifadesi yokken sıralamayı göndermez', () => {
    expect(toApiParams({ ...EMPTY_SEARCH, sort: 'relevance' }).has('sort')).toBe(false)
    expect(toApiParams({ ...EMPTY_SEARCH, q: 'deprem', sort: 'newest' }).get('sort')).toBe('newest')
  })

  it("filtreleri API'nin beklediği adlarla gönderir", () => {
    const params = toApiParams({
      ...EMPTY_SEARCH,
      q: 'seçim',
      sources: ['TRT', 'NTV'],
      language: 'tr',
      categories: ['WORLD'],
    })

    expect(Object.fromEntries(params)).toEqual({
      q: 'seçim',
      sources: 'TRT,NTV',
      language: 'tr',
      categories: 'WORLD',
      page: '0',
      size: '20',
    })
  })
})
