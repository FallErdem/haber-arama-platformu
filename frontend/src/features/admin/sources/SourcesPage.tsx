import { useQuery } from '@tanstack/react-query'
import { cn } from 'cn'
import { useState } from 'react'
import { useLocale } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { fetchSources, type SourceOverview } from '../../../api/adminSources'
import { useAccessToken } from '../../../auth/accessToken'
import { Button } from '../../../components/ui/button'
import { formatPublishedAt } from '../../../lib/time'
import { CreateSourceDialog } from './CreateSourceDialog'

/**
 * Yönetim paneli: Kaynaklar (ekran akışları 5.2; FG-YP-04, FG-YP-06). Her kaynakta etkin olup olmadığı,
 * besleme sayısı, hatalı besleme sayısı ve son başarılı toplama. Hatalı beslemesi olan kaynak dikkat çekecek
 * şekilde işaretlenir.
 */
export function SourcesPage() {
  const { t } = useTranslation()
  const accessToken = useAccessToken()
  const [isCreateOpen, setCreateOpen] = useState(false)
  const sources = useQuery({ queryKey: ['admin-sources'], queryFn: () => fetchSources(accessToken) })

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-semibold tracking-tight">{t('admin.sources.title')}</h1>
        <Button onPress={() => setCreateOpen(true)}>{t('admin.sources.add')}</Button>
      </div>
      <CreateSourceDialog isOpen={isCreateOpen} onOpenChange={setCreateOpen} />

      {sources.isPending ? (
        <p className="text-muted-foreground">{t('admin.sources.loading')}</p>
      ) : sources.isError ? (
        <div role="alert">
          <p>{t('admin.sources.loadFailed')}</p>
          <Button variant="outline" className="mt-4" onPress={() => void sources.refetch()}>
            {t('admin.retry')}
          </Button>
        </div>
      ) : (
        <ul className="divide-y divide-border border-t border-border">
          {sources.data.items.map((source) => (
            <li key={source.id}>
              <SourceRow source={source} />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function SourceRow({ source }: { source: SourceOverview }) {
  const { t } = useTranslation()
  const { locale } = useLocale()
  const hasFailures = source.failingFeedCount > 0

  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 py-4">
      <div className="min-w-0 flex-1 basis-56">
        <Link to={`/admin/sources/${source.id}`} className="font-medium underline-offset-4 hover:underline">
          {source.name}
        </Link>
        <p className="text-xs text-muted-foreground">
          {source.code} · {t(`languages.${source.language}`)} · {source.readerType}
        </p>
      </div>
      {/* Sabit genişlikli sütunlar: metinlerin uzunluğu değişse de ("1 besleme", "10 besleme") satırlar hizalı kalır. */}
      <div className="w-24">
        <span
          className={cn(
            'rounded-full border px-2.5 py-0.5 text-xs',
            source.enabled ? 'border-border' : 'border-dashed text-muted-foreground',
          )}
        >
          {source.enabled ? t('admin.sources.enabled') : t('admin.sources.disabled')}
        </span>
      </div>
      <div className="w-28 text-sm">
        <p>{t('admin.sources.feedCount', { count: source.feedCount })}</p>
        {/* Hatalı besleme: renk tek başına bilgi taşımaz, sayı da yazılır (WCAG 1.4.1). */}
        <p className={cn('text-xs', hasFailures ? 'font-medium text-destructive' : 'text-muted-foreground')}>
          {t('admin.sources.failingFeedCount', { count: source.failingFeedCount })}
        </p>
      </div>
      <p className="w-44 text-xs text-muted-foreground">
        {source.lastSuccessAt
          ? t('admin.sources.lastSuccess', { time: formatPublishedAt(source.lastSuccessAt, locale) })
          : t('admin.sources.neverSucceeded')}
      </p>
    </div>
  )
}
