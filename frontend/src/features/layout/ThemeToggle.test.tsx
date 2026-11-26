import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import { ThemeToggle } from './ThemeToggle'

describe('ThemeToggle', () => {
  afterEach(() => {
    document.documentElement.classList.remove('dark')
    localStorage.clear()
  })

  it('açık temadayken basılınca koyu temaya geçer ve seçimi saklar', async () => {
    render(<ThemeToggle />)
    const toggle = screen.getByRole('button', { name: 'Koyu tema' })
    expect(toggle).toHaveAttribute('aria-pressed', 'false')
    // Simge şu anki temayı gösterir: açıkta güneş, koyuda ay.
    expect(toggle.querySelector('.lucide-sun')).not.toBeNull()

    await userEvent.click(toggle)

    expect(document.documentElement).toHaveClass('dark')
    expect(localStorage.getItem('theme')).toBe('dark')
    expect(toggle).toHaveAttribute('aria-pressed', 'true')
    expect(toggle.querySelector('.lucide-moon')).not.toBeNull()
  })

  it('açılışta koyu tema uygulanmışsa basılı başlar ve basılınca açık temaya döner', async () => {
    // Açılıştaki temayı index.html'deki betik koyar; burada onun yerine sınıf elle eklenir.
    document.documentElement.classList.add('dark')
    render(<ThemeToggle />)
    const toggle = screen.getByRole('button', { name: 'Koyu tema' })
    expect(toggle).toHaveAttribute('aria-pressed', 'true')

    await userEvent.click(toggle)

    expect(document.documentElement).not.toHaveClass('dark')
    expect(localStorage.getItem('theme')).toBe('light')
  })
})
