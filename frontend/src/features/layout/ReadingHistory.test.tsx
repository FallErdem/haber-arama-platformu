import { act, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { I18nProvider } from 'react-aria-components'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it } from 'vitest'
import type { Me } from '../../api/me'
import { CurrentUserContext } from '../../auth/currentUser'
import { rememberArticle } from '../../lib/readingHistory'
import { ReadingHistory } from './ReadingHistory'

const USER: Me = { id: 'u1', email: 'u@example.test', displayName: null, role: 'USER', status: 'ACTIVE' }

const article = (n: number) => ({
  id: `0193f1a2-0000-7000-8000-00000000000${n}`,
  title: `Okunan haber ${n}`,
  sourceName: 'TRT Haber',
  language: 'tr',
})

function renderFor(user: Me = USER) {
  render(
    <CurrentUserContext value={user}>
      <I18nProvider locale="tr-TR">
        <MemoryRouter>
          <ReadingHistory />
        </MemoryRouter>
      </I18nProvider>
    </CurrentUserContext>,
  )
}

const titles = () =>
  within(screen.getByRole('list'))
    .getAllByRole('link')
    .map((link) => link.textContent)

describe('ReadingHistory', () => {
  afterEach(() => {
    localStorage.clear()
  })

  it('geçmiş boşken ne göreceğini söyler', () => {
    renderFor()

    expect(screen.getByText('Açtığın haberler burada görünür.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Okuma geçmişini temizle' })).not.toBeInTheDocument()
  })

  it('açılan haber anında en üste düşer; yeniden açılan haber tekrarlanmaz', () => {
    renderFor()

    act(() => rememberArticle(USER.id, article(1)))
    act(() => rememberArticle(USER.id, article(2)))
    expect(titles()).toEqual(['Okunan haber 2', 'Okunan haber 1'])

    act(() => rememberArticle(USER.id, article(1)))
    expect(titles()).toEqual(['Okunan haber 1', 'Okunan haber 2'])
    expect(screen.getByRole('link', { name: 'Okunan haber 1' })).toHaveAttribute('href', `/articles/${article(1).id}`)
  })

  it('en fazla 9 haber tutar', () => {
    renderFor()

    act(() => [1, 2, 3, 4, 5, 6, 7, 8, 9].forEach((n) => rememberArticle(USER.id, article(n))))
    act(() => rememberArticle(USER.id, { ...article(1), id: '0193f1a2-0000-7000-8000-000000000010', title: 'Onuncu' }))

    expect(titles()).toHaveLength(9)
    expect(titles()[0]).toBe('Onuncu')
    expect(titles()).not.toContain('Okunan haber 1')
  })

  it('başka bir kullanıcının geçmişini göstermez', () => {
    act(() => rememberArticle('baska-kullanici', article(1)))

    renderFor()

    expect(screen.getByText('Açtığın haberler burada görünür.')).toBeInTheDocument()
  })

  it('Temizle geçmişi siler', async () => {
    rememberArticle(USER.id, article(1))
    renderFor()

    await userEvent.click(screen.getByRole('button', { name: 'Okuma geçmişini temizle' }))

    expect(screen.getByText('Açtığın haberler burada görünür.')).toBeInTheDocument()
  })
})
