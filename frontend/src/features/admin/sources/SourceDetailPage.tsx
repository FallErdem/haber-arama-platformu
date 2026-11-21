import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { cn } from 'cn'
import { ArrowLeftIcon } from 'lucide-react'
import { useState } from 'react'
import { useLocale } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router'
import {
  fetchSource,
  requestFetch,
  updateFeed,
  updateSource,
  type ManagedFeed,
  type ManagedSource,
} from '../../../api/adminSources'
import { ApiError } from '../../../api/client'
import { useAccessToken } from '../../../auth/accessToken'
import { Button } from '../../../components/ui/button'
import { formatPublishedAt } from '../../../lib/time'
import { NotFoundPage } from '../../errors/NotFoundPage'
import { adminErrorMessage, isStaleError } from '../adminErrors'
import { FeedDialog } from './FeedDialog'
import { PurgeDialog } from './PurgeDialog'
import { SourceSettingsForm } from './SourceSettingsForm'

/** İçerik silinirken detayın yeniden istenme aralığı: silme bitince durum kendiliğinden kalkar. */
const PURGE_POLL_MS = 5000

/** İşlemin sonucu: başarı veya hata mesajı; ekranın üstünde tek yerde duyurulur. */
interface Notice {
  kind: 'success' | 'error'
  text: string
}

/**
 * Yönetim paneli: kaynak detayı (ekran akışları 5.2; FG-YP-04, FG-YP-06 – 08, FG-YP-14). Kaynağın ayarları,
 * etkinleştirme, "Şimdi topla", "İçeriği sil" ve beslemeleri sağlık durumlarıyla. Her değişiklik kaydın
 * sürümüyle gönderilir; kayıt bu arada değiştiyse kullanıcıya söylenir ve ekran yenilenir.
 */
export function SourceDetailPage() {
  const { sourceId = '' } = useParams()
  const { t } = useTranslation()
  const accessToken = useAccessToken()
  const source = useQuery({
    queryKey: ['admin-source', sourceId],
    queryFn: () => fetchSource(accessToken, sourceId),
    // Silmeyi işçi yapar; sürerken detay aralıklarla yeniden istenir, bitince istek boşalır ve yenileme durur.
    refetchInterval: (query) => (query.state.data?.purgeRequestedAt ? PURGE_POLL_MS : false),
  })

  if (source.error instanceof ApiError && (source.error.status === 404 || source.error.status === 400)) {
    return <NotFoundPage />
  }

  return (
    <div>
      <Link
        to="/admin/sources"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeftIcon aria-hidden className="size-4" />
        {t('admin.sources.back')}
      </Link>
      {source.isPending ? (
        <p className="mt-6 text-muted-foreground">{t('admin.sources.loading')}</p>
      ) : source.isError ? (
        <div role="alert" className="mt-6">
          <p>{t('admin.sources.detailLoadFailed')}</p>
          <Button variant="outline" className="mt-4" onPress={() => void source.refetch()}>
            {t('admin.retry')}
          </Button>
        </div>
      ) : (
        <SourceView source={source.data} />
      )}
    </div>
  )
}

function SourceView({ source }: { source: ManagedSource }) {
  const { t } = useTranslation()
  const accessToken = useAccessToken()
  const queryClient = useQueryClient()
  const [notice, setNotice] = useState<Notice | null>(null)
  const [isAddFeedOpen, setAddFeedOpen] = useState(false)
  const [isPurgeOpen, setPurgeOpen] = useState(false)
  const isPurging = source.purgeRequestedAt !== null

  /** Değişiklikten sonra detay ve liste yeniden istenir; hata kaydın eskidiğini söylüyorsa yine yenilenir. */
  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['admin-source', source.id] }),
      queryClient.invalidateQueries({ queryKey: ['admin-sources'] }),
    ])
  const onError = (error: Error) => {
    setNotice({ kind: 'error', text: adminErrorMessage(error, t) })
    if (isStaleError(error)) void refresh()
  }

  const toggle = useMutation({
    mutationFn: () => updateSource(accessToken, source.id, { enabled: !source.enabled, version: source.version }),
    onSuccess: async (updated) => {
      setNotice({
        kind: 'success',
        text: updated.enabled ? t('admin.sources.enabledNotice') : t('admin.sources.disabledNotice'),
      })
      await refresh()
    },
    onError,
  })
  const fetchNow = useMutation({
    mutationFn: () => requestFetch(accessToken, source.id),
    onSuccess: async ({ feedCount }) => {
      setNotice({ kind: 'success', text: t('admin.sources.fetchRequested', { count: feedCount }) })
      await refresh()
    },
    onError,
  })

  return (
    <>
      <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{source.name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {source.code} · {t(`languages.${source.language}`)} · {source.readerType} ·{' '}
            {source.enabled ? t('admin.sources.enabled') : t('admin.sources.disabled')} ·{' '}
            {t('admin.sources.articleCount', { count: source.articleCount })}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {/* Devre dışı kaynağın beslemeleri okunmaz; elle toplama da yapılamaz (sözleşme 6.2). */}
          <Button
            variant="outline"
            isDisabled={!source.enabled || fetchNow.isPending}
            onPress={() => fetchNow.mutate()}
          >
            {t('admin.sources.fetchNow')}
          </Button>
          {/* İçerik silinirken kaynak etkinleştirilemez: silme sürerken yeni haberler eklenirdi. */}
          <Button
            variant={source.enabled ? 'outline' : 'default'}
            isDisabled={toggle.isPending || isPurging}
            onPress={() => toggle.mutate()}
          >
            {source.enabled ? t('admin.sources.disable') : t('admin.sources.enable')}
          </Button>
          {/* İçerik yalnızca devre dışı kaynakta silinebilir (sözleşme 6.2). Düğme her zaman görünür; kaynak
              etkinse pencere açılmaz, önce devre dışı bırakılması gerektiği söylenir. */}
          <Button
            variant="destructive"
            isDisabled={isPurging || source.articleCount === 0}
            onPress={() =>
              source.enabled
                ? setNotice({ kind: 'error', text: t('admin.sources.purgeNeedsDisabled') })
                : setPurgeOpen(true)
            }
          >
            {t('admin.sources.purge')}
          </Button>
        </div>
      </div>
      <PurgeDialog
        source={source}
        isOpen={isPurgeOpen}
        onOpenChange={setPurgeOpen}
        onRequested={() => setNotice({ kind: 'success', text: t('admin.sources.purgeRequested') })}
        refresh={refresh}
      />

      {isPurging && (
        <p role="status" className="mt-4 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm">
          {t('admin.sources.purging')}
        </p>
      )}

      {notice && (
        <p
          role={notice.kind === 'error' ? 'alert' : 'status'}
          className={cn(
            'mt-4 rounded-lg border px-3 py-2 text-sm',
            notice.kind === 'error' ? 'border-destructive/30 bg-destructive/5' : 'border-border bg-muted/50',
          )}
        >
          {notice.text}
        </p>
      )}

      <section className="mt-8">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-3">
          <h2 className="text-lg font-semibold">{t('admin.feeds.title')}</h2>
          <div className="flex items-center gap-3">
            <Link
              to={`/admin/ingestion-runs?sourceId=${source.id}`}
              className="text-sm text-primary underline-offset-4 hover:underline"
            >
              {t('admin.sources.history')}
            </Link>
            <Button size="sm" onPress={() => setAddFeedOpen(true)}>
              {t('admin.feeds.add')}
            </Button>
          </div>
        </div>
        <FeedDialog sourceId={source.id} isOpen={isAddFeedOpen} onOpenChange={setAddFeedOpen} onSaved={refresh} />
        {source.feeds.length === 0 ? (
          <p className="py-8 text-center text-muted-foreground">{t('admin.feeds.empty')}</p>
        ) : (
          <ul className="divide-y divide-border">
            {source.feeds.map((feed) => (
              <li key={feed.id}>
                <FeedRow feed={feed} onSaved={refresh} onError={onError} />
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mt-10">
        <h2 className="border-b border-border pb-3 text-lg font-semibold">{t('admin.sources.settings')}</h2>
        {/* key: kayıt değişince (yeni sürüm) form güncel değerlerle yeniden kurulur. */}
        <SourceSettingsForm key={source.version} source={source} onSaved={refresh} onError={onError} />
      </section>
    </>
  )
}

interface FeedRowProps {
  feed: ManagedFeed
  onSaved: () => Promise<unknown>
  onError: (error: Error) => void
}

/** Bir besleme: ayarları, sağlık durumu (FG-YP-06), düzenleme ve açma/kapama. */
function FeedRow({ feed, onSaved, onError }: FeedRowProps) {
  const { t } = useTranslation()
  const { locale } = useLocale()
  const accessToken = useAccessToken()
  const [isEditOpen, setEditOpen] = useState(false)
  const toggle = useMutation({
    mutationFn: () => updateFeed(accessToken, feed.id, { enabled: !feed.enabled, version: feed.version }),
    onSuccess: onSaved,
    onError,
  })
  const toggleLabel = feed.enabled ? t('admin.feeds.disable') : t('admin.feeds.enable')
  const status = feed.enabled
    ? t('admin.feeds.status.enabled')
    : feed.disabledReason === 'AUTO'
      ? t('admin.feeds.status.auto')
      : t('admin.feeds.status.manual')

  return (
    <div className="flex flex-wrap items-start gap-x-6 gap-y-2 py-4">
      <div className="min-w-0 flex-1 basis-72">
        <p className="font-medium">{feed.name}</p>
        <p className="truncate text-xs text-muted-foreground">{feed.url}</p>
        <p className="mt-1 text-xs text-muted-foreground">
          {feed.defaultCategoryCode ? t(`categories.${feed.defaultCategoryCode}`) : t('admin.feeds.noCategory')}
          {feed.useItemCategories && ` · ${t('admin.feeds.itemCategories')}`} ·{' '}
          {t('admin.feeds.everyMinutes', { count: feed.fetchIntervalMinutes })}
        </p>
      </div>
      <div className="w-56 text-xs">
        <p className={cn('font-medium', feed.disabledReason === 'AUTO' && 'text-destructive')}>{status}</p>
        {feed.consecutiveFailures > 0 && (
          <p className="text-destructive">{t('admin.feeds.failures', { count: feed.consecutiveFailures })}</p>
        )}
        {feed.lastError && <p className="text-muted-foreground">{feed.lastError}</p>}
        <p className="text-muted-foreground">
          {feed.lastSuccessAt
            ? t('admin.sources.lastSuccess', { time: formatPublishedAt(feed.lastSuccessAt, locale) })
            : t('admin.sources.neverSucceeded')}
        </p>
        {feed.manualFetchRequestedAt && <p className="text-muted-foreground">{t('admin.feeds.fetchPending')}</p>}
      </div>
      {/* Erişilebilir ada beslemenin adı eklenir: listede aynı adlı düğmeler ekran okuyucuda ayırt edilsin.
          Görünen metin adın başında kalır (WCAG 2.5.3). */}
      <div className="flex gap-2">
        <Button
          size="sm"
          variant="ghost"
          aria-label={`${t('admin.feeds.edit')}: ${feed.name}`}
          onPress={() => setEditOpen(true)}
        >
          {t('admin.feeds.edit')}
        </Button>
        <Button
          size="sm"
          variant="outline"
          aria-label={`${toggleLabel}: ${feed.name}`}
          isDisabled={toggle.isPending}
          onPress={() => toggle.mutate()}
        >
          {toggleLabel}
        </Button>
      </div>
      {/* key: besleme değişince (yeni sürüm) pencere güncel değerlerle yeniden kurulur. */}
      <FeedDialog
        key={feed.version}
        sourceId={feed.sourceId}
        feed={feed}
        isOpen={isEditOpen}
        onOpenChange={setEditOpen}
        onSaved={onSaved}
      />
    </div>
  )
}
