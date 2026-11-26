/*
 * Açık ve koyu tema. Tema <html> öğesindeki .dark sınıfıyla uygulanır; renkler index.css'tedir.
 *
 * Açılıştaki temayı index.html'deki betik, sayfa çizilmeden önce koyar: kullanıcı daha önce seçim yaptıysa
 * o, yapmadıysa işletim sisteminin ayarı. Buradaki kod yalnızca düğmeyle yapılan değişikliği uygular ve
 * seçimi tarayıcıda saklar; böylece bir sonraki açılışta da aynı tema gelir.
 */
import { useState } from 'react'

export type Theme = 'light' | 'dark'

/** Seçimin tarayıcıdaki anahtarı. index.html'deki betik de bu anahtarı okur; değişirse orası da değişmeli. */
export const THEME_STORAGE_KEY = 'theme'

/** Sayfada şu an uygulanan tema. */
export function currentTheme(): Theme {
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light'
}

/** Temayı uygular ve seçimi saklar. */
export function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle('dark', theme === 'dark')
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme)
  } catch {
    // Tarayıcı depolamayı engelliyorsa tema bu sayfada yine değişir; yalnızca sonraki açılışta hatırlanmaz.
  }
}

/** Şu anki tema ve onu değiştiren fonksiyon. Başlangıç değeri, açılışta index.html'nin koyduğu temadır. */
export function useTheme(): { theme: Theme; setTheme: (theme: Theme) => void } {
  const [theme, setThemeState] = useState<Theme>(currentTheme)

  const setTheme = (next: Theme) => {
    applyTheme(next)
    setThemeState(next)
  }

  return { theme, setTheme }
}
