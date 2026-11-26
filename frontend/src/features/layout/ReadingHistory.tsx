import { useLocale } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { useCurrentUser } from '../../auth/currentUser'
import { Button } from '../../components/ui/button'
import { clearHistory, useReadingHistory } from '../../lib/readingHistory'
import { formatPublishedAt } from '../../lib/time'

/**
 * Haber sayfalarının sağındaki okuma geçmişi: kullanıcının açtığı son haberler, en yenisi başta, açıldığı zamanla.
 * Haber açıldığı anda listeye düşer. Geçmiş kişisel bir bilgi olduğu için "Temizle" ile silinebilir; tarayıcıda
 * saklanır, sunucuya gitmez (lib/readingHistory.ts).
 */
export function ReadingHistory() {
  const { t } = useTranslation()
  const { locale } = useLocale()
  const currentUser = useCurrentUser()
  const history = useReadingHistory(currentUser.id)

  return (
    <section aria-labelledby="reading-history">
      <div className="flex items-baseline justify-between gap-4 border-b-2 border-primary pb-2">
        <h2 id="reading-history" className="text-lg font-semibold">
          {t('history.title')}
        </h2>
        {history.length > 0 && (
          <Button
            variant="link"
            size="sm"
            className="h-auto px-0"
            aria-label={t('history.clearLabel')}
            onPress={() => clearHistory(currentUser.id)}
          >
            {t('history.clear')}
          </Button>
        )}
      </div>

      {history.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">{t('history.empty')}</p>
      ) : (
        <ol className="divide-y divide-border">
          {history.map((entry) => (
            <li key={entry.id} lang={entry.language} className="py-3">
              <p className="text-xs text-muted-foreground">
                {entry.sourceName}
                <span aria-hidden> · </span>
                <time dateTime={entry.readAt}>{formatPublishedAt(entry.readAt, locale)}</time>
              </p>
              <Link
                to={`/articles/${entry.id}`}
                className="mt-1 block font-heading text-[0.95rem] leading-snug font-semibold decoration-1 underline-offset-4 hover:underline"
              >
                {entry.title}
              </Link>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
