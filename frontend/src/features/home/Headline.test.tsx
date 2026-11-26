import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { I18nProvider } from 'react-aria-components'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ArticleSearchItem } from '../../api/articles'
import { AccessTokenContext } from '../../auth/accessToken'
import { Headline } from './Headline'

function item(n: number, overrides: Partial<ArticleSearchItem> = {}): ArticleSearchItem {
  return {
    id: `0193f1a2-0000-7000-8000-00000000000${n}`,
    title: `Haber ${n}`,
    summary: null,
    source: { code: 'TRT', name: 'TRT Haber' },
    language: 'tr',
    itemType: 'ARTICLE',
    categories: ['BREAKING'],
    publishedAt: '2026-11-26T12:00:00Z',
    url: `https://www.trthaber.com/${n}`,
    image: { url: `/api/v1/media/m${n}`, width: 1200, height: 675 },
    otherSourcesCount: 0,
    saved: false,
    ...overrides,
  }
}

/** Kategoriye göre yanıt verir; `searches` gönderilen istekleri tutar. */
function stubApi(byCategory: Record<string, ArticleSearchItem[]>) {
  const searches: URLSearchParams[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn((input: string) => {
      const params = new URL(input, 'http://haber.localhost').searchParams
      searches.push(params)
      const items = byCategory[params.get('categories') ?? ''] ?? []
      return Promise.resolve(
        Response.json({ items, page: 0, size: 20, totalElements: items.length, totalPages: 1, totalRelation: 'eq' }),
      )
    }),
  )
  return searches
}

function renderHeadline() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AccessTokenContext value="test-token">
        <I18nProvider locale="tr-TR">
          <MemoryRouter>
            <Headline />
          </MemoryRouter>
        </I18nProvider>
      </AccessTokenContext>
    </QueryClientProvider>,
  )
}

/** Görselin altındaki ilerleme çubuğu. */
function progress(): HTMLElement {
  return document.querySelector('[data-slot="headline-progress"]')!
}

/**
 * Çubuğun dolmasını (animasyonun bitişini) gönderir; jsdom animasyon çalıştırmaz. jsdom'da AnimationEvent olmadığı
 * için React bitişi önekli adla (webkitAnimationEnd) dinler, gerçek tarayıcıda "animationend" ile. İkisi de
 * gönderilir; React yalnızca birini dinlediği için geçiş bir kez olur.
 */
function finishProgress() {
  fireEvent(progress(), new Event('animationend', { bubbles: true }))
  fireEvent(progress(), new Event('webkitAnimationEnd', { bubbles: true }))
}

/** Şu an gösterilen manşet: görünmeyenler aria-hidden ve inert'tir. */
function activeSlide() {
  const slides = screen.getAllByRole('group', { hidden: true })
  const visible = slides.filter((slide) => slide.getAttribute('aria-hidden') !== 'true')
  expect(visible).toHaveLength(1)
  return visible[0]
}

describe('Headline', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('görselli son dakika haberlerini gösterir; görünmeyen haberler odaklanamaz', async () => {
    const searches = stubApi({
      BREAKING: [1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => item(n, n === 2 ? { image: null } : {})),
    })
    renderHeadline()

    await screen.findByRole('region', { name: 'Manşet' })
    // Görselsiz haber (2) alınmaz; ilk 8 görselli haber.
    const slides = screen.getAllByRole('group', { hidden: true })
    expect(slides.map((slide) => within(slide).getByRole('link', { hidden: true }).textContent)).toEqual([
      'Haber 1',
      'Haber 3',
      'Haber 4',
      'Haber 5',
      'Haber 6',
      'Haber 7',
      'Haber 8',
      'Haber 9',
    ])
    expect(within(activeSlide()).getByRole('link')).toHaveAttribute('href', `/articles/${item(1).id}`)
    expect(slides[1]).toHaveAttribute('inert')
    // Yeterli görselli son dakika olduğu için Gündem istenmez.
    expect(searches.map((params) => params.get('categories'))).toEqual(['BREAKING'])
  })

  it('görselli son dakika yetmezse Gündem haberleriyle tamamlar', async () => {
    stubApi({ BREAKING: [item(1)], GENERAL: [item(1), item(2, { categories: ['GENERAL'] })] })
    renderHeadline()

    await screen.findByRole('region', { name: 'Manşet' })
    const titles = screen
      .getAllByRole('group', { hidden: true })
      .map((slide) => within(slide).getByRole('link', { hidden: true }).textContent)
    // Hem son dakikada hem Gündem'de olan haber (1) iki kez gösterilmez.
    expect(titles).toEqual(['Haber 1', 'Haber 2'])
  })

  it('çubuk 10 saniyede dolar; dolunca sonraki habere geçer', async () => {
    stubApi({ BREAKING: [item(1), item(3), item(4)] })
    renderHeadline()
    await screen.findByRole('region', { name: 'Manşet' })
    expect(within(activeSlide()).getByRole('link')).toHaveTextContent('Haber 1')
    expect(progress().style.animation).toContain('10000ms')
    expect(progress().style.animationPlayState).toBe('running')

    finishProgress()
    expect(within(activeSlide()).getByRole('link')).toHaveTextContent('Haber 3')
  })

  it('fare görselin üzerindeyken çubuk bekler; Durdur basılınca da bekler ve geçmez', async () => {
    stubApi({ BREAKING: [item(1), item(3), item(4)] })
    renderHeadline()
    await screen.findByRole('region', { name: 'Manşet' })

    await userEvent.hover(activeSlide())
    expect(progress().style.animationPlayState).toBe('paused')
    await userEvent.unhover(activeSlide())
    expect(progress().style.animationPlayState).toBe('running')

    // Düğmelerin üzerine gelmek döngüyü durdurmaz; Durdur'a basmak durdurur.
    await userEvent.click(screen.getByRole('button', { name: 'Manşetin değişmesini durdur' }))
    expect(progress().style.animationPlayState).toBe('paused')
    finishProgress()
    expect(within(activeSlide()).getByRole('link')).toHaveTextContent('Haber 1')
    expect(screen.getByRole('button', { name: 'Manşetin değişmesini başlat' })).toBeInTheDocument()
  })

  it('oklar ve noktalarla haberler arasında geçilir; sondan başa döner', async () => {
    stubApi({ BREAKING: [item(1), item(3), item(4)] })
    renderHeadline()
    await screen.findByRole('region', { name: 'Manşet' })

    await userEvent.click(screen.getByRole('button', { name: 'Önceki manşet' }))
    expect(within(activeSlide()).getByRole('link')).toHaveTextContent('Haber 4')

    await userEvent.click(screen.getByRole('button', { name: 'Sonraki manşet' }))
    expect(within(activeSlide()).getByRole('link')).toHaveTextContent('Haber 1')

    await userEvent.click(screen.getByRole('button', { name: '2. manşeti göster' }))
    expect(within(activeSlide()).getByRole('link')).toHaveTextContent('Haber 3')
    expect(screen.getByRole('button', { name: '2. manşeti göster' })).toHaveAttribute('aria-current', 'true')
  })

  it('görselli haber yoksa manşeti göstermez', async () => {
    const searches = stubApi({ BREAKING: [item(1, { image: null })], GENERAL: [] })
    renderHeadline()

    await vi.waitFor(() => expect(searches).toHaveLength(2))
    expect(screen.queryByRole('region', { name: 'Manşet' })).not.toBeInTheDocument()
  })
})
