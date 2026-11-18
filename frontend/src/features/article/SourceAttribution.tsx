import { ExternalLinkIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { ArticleDetail } from '../../api/articles'

/**
 * Lisansı atıf isteyen kaynaklar: kaynak kodu → lisans politikasının adresi. Metinler dil
 * dosyasındadır (`article.license.<kod>`). Arayüz atfı kaynağın koduna göre gösterir (API sözleşmesi
 * 4.2, ADR-0009). NYT logosu bu listeye NYT kaynağıyla birlikte eklenecek.
 */
const LICENSES: Record<string, { policyUrl: string }> = {
  // Adres Global Voices'ın kendi besleme sayfasından alındı; beslemenin <copyright> alanı da buraya yönlendirir.
  GLOBALVOICES: { policyUrl: 'https://globalvoices.org/about/global-voices-attribution-policy/' },
}

const EXTERNAL = { target: '_blank', rel: 'noopener noreferrer' } as const

/**
 * Kaynak kutusu: kaynağın adı (ana sayfasına bağlantı), atıf metni, gerekiyorsa lisans bilgisi ve
 * özgün habere bağlantı (FG-AR-07). Özgün haber yeni sekmede açılır; sayfası uygulamanın içinde
 * gösterilmez (ekran akışları 2. bölüm).
 */
export function SourceAttribution({ article }: { article: ArticleDetail }) {
  const { t } = useTranslation()
  const { source } = article
  const license = LICENSES[source.code]

  return (
    <aside aria-label={t('article.source')} className="mt-10 border-t border-border pt-6">
      <p className="text-sm text-muted-foreground">
        {t('article.source')}:{' '}
        <a href={source.homepageUrl} {...EXTERNAL} className="font-medium text-foreground hover:underline">
          {source.name}
        </a>
        {source.attributionText && source.attributionText !== source.name && <> · {source.attributionText}</>}
      </p>
      {license && (
        <p className="mt-2 text-sm text-muted-foreground">
          {t(`article.license.${source.code}.text`)}{' '}
          <a href={license.policyUrl} {...EXTERNAL} className="text-primary underline-offset-4 hover:underline">
            {t(`article.license.${source.code}.policy`)}
          </a>
        </p>
      )}
      <a
        href={article.url}
        {...EXTERNAL}
        className="mt-5 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/85 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
      >
        {t('article.readAtSource')}
        <ExternalLinkIcon aria-hidden className="size-4" />
      </a>
    </aside>
  )
}
