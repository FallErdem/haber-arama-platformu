import { cn } from 'cn'
import { MoonIcon, SunIcon } from 'lucide-react'
import { ToggleButton } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { buttonVariants } from '../../components/ui/button-variants'
import { useTheme } from '../../lib/theme'

/**
 * Üst çubuktaki koyu tema düğmesi. Kaydetme düğmesiyle aynı kalıptadır: React Aria'nın aç/kapa düğmesi,
 * durumunu ekran okuyucuya `aria-pressed` ile bildirir ("Koyu tema, basılı"). Adı durumla değişmez.
 * Simge şu anki temayı gösterir: açık temada güneş, koyu temada ay.
 */
export function ThemeToggle() {
  const { t } = useTranslation()
  const { theme, setTheme } = useTheme()
  const isDark = theme === 'dark'
  const Icon = isDark ? MoonIcon : SunIcon

  return (
    <ToggleButton
      isSelected={isDark}
      onChange={(selected) => setTheme(selected ? 'dark' : 'light')}
      aria-label={t('layout.darkTheme')}
      className={cn(buttonVariants({ variant: 'ghost', size: 'icon-sm' }), 'text-muted-foreground')}
    >
      <Icon aria-hidden className="size-4" />
    </ToggleButton>
  )
}
