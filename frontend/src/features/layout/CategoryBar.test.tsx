import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AccessTokenContext } from '../../auth/accessToken'
import { CategoryBar } from './CategoryBar'

const CATEGORIES = [
  { code: 'GENERAL', kind: 'TOPIC', sortOrder: 10 },
  { code: 'SPORTS', kind: 'TOPIC', sortOrder: 40 },
  { code: 'BREAKING', kind: 'TEMPORAL', sortOrder: 90 },
  { code: 'OTHER', kind: 'TOPIC', sortOrder: 100 },
]

function renderAt(path: string) {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.resolve(Response.json({ items: CATEGORIES }))),
  )
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AccessTokenContext value="test-token">
        <MemoryRouter initialEntries={[path]}>
          <CategoryBar />
        </MemoryRouter>
      </AccessTokenContext>
    </QueryClientProvider>,
  )
}

describe('CategoryBar', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('önce Son Dakika, sonra konu kategorilerini gösterir; Diğer yer almaz', async () => {
    renderAt('/')

    const nav = screen.getByRole('navigation', { name: 'Kategoriler' })
    await within(nav).findByRole('link', { name: 'Spor' })
    const links = within(nav).getAllByRole('link')
    expect(links.map((link) => link.textContent)).toEqual(['Son Dakika', 'Gündem', 'Spor'])
    expect(links[0]).toHaveAttribute('href', '/?categories=BREAKING')
    expect(links[2]).toHaveAttribute('href', '/?categories=SPORTS')
  })

  it('adreste yalnızca o kategori seçiliyse bağlantıyı bulunulan sayfa olarak işaretler', async () => {
    renderAt('/?categories=SPORTS')

    expect(await screen.findByRole('link', { name: 'Spor' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'Gündem' })).not.toHaveAttribute('aria-current')
  })

  it('başka bir filtre de varsa hiçbir bağlantıyı işaretlemez', async () => {
    renderAt('/?categories=SPORTS&q=derbi')

    expect(await screen.findByRole('link', { name: 'Spor' })).not.toHaveAttribute('aria-current')
  })
})
