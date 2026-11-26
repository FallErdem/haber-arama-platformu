import { ArrowUpIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '../../components/ui/button'

/** Sayfa bu kadar aşağı kaydırılınca düğme görünür. */
const SHOW_AFTER_PX = 800

/**
 * Uzun listelerde sağ altta beliren "Başa dön" düğmesi. Basılınca sayfa başa kayar (hareketi azaltma ayarı
 * açıksa kaymadan atlar) ve odak içeriğin başına taşınır: düğme kaybolunca klavyeyle gezen kullanıcının odağı
 * boşa düşmez.
 */
export function BackToTop() {
  const { t } = useTranslation()
  const [isVisible, setVisible] = useState(false)

  useEffect(() => {
    const update = () => setVisible(window.scrollY > SHOW_AFTER_PX)
    update()
    // passive: kaydırmayı yavaşlatmaz; dinleyici kaydırmayı engellemeyeceğini tarayıcıya söyler.
    window.addEventListener('scroll', update, { passive: true })
    return () => window.removeEventListener('scroll', update)
  }, [])

  if (!isVisible) {
    return null
  }

  const scrollToTop = () => {
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
    window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' })
    document.getElementById('main-content')?.focus({ preventScroll: true })
  }

  return (
    <Button
      variant="outline"
      size="icon-lg"
      aria-label={t('layout.backToTop')}
      onPress={scrollToTop}
      className="fixed right-4 bottom-4 z-40 rounded-full bg-background shadow-sm sm:right-6 sm:bottom-6"
    >
      <ArrowUpIcon aria-hidden />
    </Button>
  )
}
