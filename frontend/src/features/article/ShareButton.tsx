import { Share2Icon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '../../components/ui/button'

/** Kopyalandı mesajı bu kadar süre görünür; okunacak kadar uzun, ekranda kalmayacak kadar kısa. */
const MESSAGE_MS = 4000

/**
 * Paylaş düğmesi. Paylaşılan adres haberin kaynağındaki adresidir: uygulama giriş istediği için bizim
 * sayfamızın adresi, alan kişide açılmazdı. Telefonda (ve destekleyen tarayıcılarda) sistemin paylaşma menüsü
 * açılır; desteklemeyen tarayıcıda adres panoya kopyalanır ve sonuç ekran okuyucuya da duyurulur.
 */
export function ShareButton({ title, url }: { title: string; url: string }) {
  const { t } = useTranslation()
  const [result, setResult] = useState<'copied' | 'failed' | null>(null)

  useEffect(() => {
    if (result === null) return
    const timer = window.setTimeout(() => setResult(null), MESSAGE_MS)
    return () => window.clearTimeout(timer)
  }, [result])

  const share = async () => {
    if (navigator.share) {
      try {
        await navigator.share({ title, url })
        return
      } catch (error) {
        // Kullanıcı paylaşma menüsünü kapattı; hata değildir.
        if (error instanceof DOMException && error.name === 'AbortError') return
        // Başka bir hatada panoya kopyalamaya geçilir.
      }
    }
    try {
      await navigator.clipboard.writeText(url)
      setResult('copied')
    } catch {
      setResult('failed')
    }
  }

  return (
    <>
      <Button variant="ghost" size="sm" onPress={() => void share()}>
        <Share2Icon aria-hidden />
        {t('article.share')}
      </Button>
      {/* role="status" baştan sayfada durur; içine yazılan mesajı ekran okuyucu duyurur. */}
      <span role="status" className="text-xs text-muted-foreground">
        {result === 'copied' ? t('article.linkCopied') : result === 'failed' ? t('article.shareFailed') : ''}
      </span>
    </>
  )
}
