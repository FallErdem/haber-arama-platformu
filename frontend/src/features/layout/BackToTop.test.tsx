import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { BackToTop } from './BackToTop'

/** Sayfanın ne kadar kaydırıldığını değiştirir ve tarayıcı gibi "scroll" olayı gönderir. */
function scrollTo(y: number) {
  Object.defineProperty(window, 'scrollY', { value: y, configurable: true })
  act(() => {
    fireEvent.scroll(window)
  })
}

describe('BackToTop', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    Object.defineProperty(window, 'scrollY', { value: 0, configurable: true })
  })

  it('sayfa aşağı kaydırılınca görünür, yukarıda kaybolur', () => {
    render(<BackToTop />)
    expect(screen.queryByRole('button', { name: 'Başa dön' })).not.toBeInTheDocument()

    scrollTo(1200)
    expect(screen.getByRole('button', { name: 'Başa dön' })).toBeInTheDocument()

    scrollTo(100)
    expect(screen.queryByRole('button', { name: 'Başa dön' })).not.toBeInTheDocument()
  })

  it('basılınca sayfayı başa kaydırır ve odağı içeriğin başına taşır', async () => {
    const scroll = vi.fn()
    vi.stubGlobal('scrollTo', scroll)
    render(
      <>
        <main id="main-content" tabIndex={-1} />
        <BackToTop />
      </>,
    )
    scrollTo(1200)

    await userEvent.click(screen.getByRole('button', { name: 'Başa dön' }))

    expect(scroll).toHaveBeenCalledWith(expect.objectContaining({ top: 0 }))
    expect(document.getElementById('main-content')).toHaveFocus()
  })
})
