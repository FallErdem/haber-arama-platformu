import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { cn } from 'cn'
import type { ReactNode } from 'react'
import { useLocale } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { fetchStats, type ComponentStatus, type Stats } from '../../../api/adminStats'
import { useAccessToken } from '../../../auth/accessToken'
import { Button } from '../../../components/ui/button'
import { formatPublishedAt, TIME_ZONE } from '../../../lib/time'

/** Pano bu aralıkla kendiliğinden yenilenir. */
const REFRESH_MS = 30_000

/** İşçinin son etkinliği bundan eskiyse uyarı gösterilir (ekran akışları, "Pano"). */
const WORKER_STALE_MS = 30 * 60_000

/**
 * Yönetim paneli: pano (ekran akışları, "Pano"; FG-YP-12). Üstte dört özet (haberler, kullanıcılar,
 * beslemeler, arama indeksi), altında sistemin durumu ve kaynak bazında haber sayıları. 30 saniyede bir
 * kendiliğinden yenilenir.
 */
export function DashboardPage() {
  const { t } = useTranslation()
  const { locale } = useLocale()
  const accessToken = useAccessToken()
  const stats = useQuery({
    queryKey: ['admin-stats'],
    queryFn: () => fetchStats(accessToken),
    refetchInterval: REFRESH_MS,
    placeholderData: keepPreviousData,
  })

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h1 className="text-3xl font-semibold tracking-tight">{t('admin.dashboard.title')}</h1>
        {stats.isSuccess && (
          <p className="text-sm text-muted-foreground">
            {t('admin.dashboard.updatedAt', { time: formatClock(stats.dataUpdatedAt, locale) })}
          </p>
        )}
      </div>
      {stats.isPending ? (
        <p className="text-muted-foreground">{t('admin.dashboard.loading')}</p>
      ) : stats.isError ? (
        <div role="alert">
          <p>{t('admin.dashboard.loadFailed')}</p>
          <Button variant="outline" className="mt-4" onPress={() => void stats.refetch()}>
            {t('admin.retry')}
          </Button>
        </div>
      ) : (
        <Dashboard stats={stats.data} fetchedAt={stats.dataUpdatedAt} />
      )}
    </div>
  )
}

/** @param fetchedAt verinin alındığı an (ms); işçinin son etkinliği bu ana göre değerlendirilir */
function Dashboard({ stats, fetchedAt }: { stats: Stats; fetchedAt: number }) {
  const { t } = useTranslation()
  const { locale } = useLocale()
  const number = new Intl.NumberFormat(locale)
  const { articles, users, feeds, searchIndex, components } = stats
  const workerActivity = components.workerLastActivityAt
  const isWorkerStale = workerActivity === null || fetchedAt - Date.parse(workerActivity) > WORKER_STALE_MS

  return (
    <>
      {isWorkerStale && (
        <p role="alert" className="mb-6 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm">
          {workerActivity === null
            ? t('admin.dashboard.workerNeverAlert')
            : t('admin.dashboard.workerStale', { time: formatPublishedAt(workerActivity, locale) })}
        </p>
      )}

      {/* Özetler: ince çizgilerle ayrılmış dört kutu (gap-px ve çizgi renginde zemin). */}
      <dl className="grid gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label={t('admin.dashboard.articles')} value={number.format(articles.total)}>
          {t('admin.dashboard.newArticles', { count: articles.last24h, formatted: number.format(articles.last24h) })}
        </StatCard>
        <StatCard
          label={t('admin.dashboard.users')}
          value={number.format(users.ACTIVE)}
          unit={t('admin.dashboard.activeUsers')}
        >
          {users.PENDING > 0 ? (
            <Link
              to="/admin/users?status=PENDING"
              className="font-medium text-primary underline-offset-4 hover:underline"
            >
              {t('admin.dashboard.pendingUsers', { count: users.PENDING })}
            </Link>
          ) : (
            t('admin.dashboard.noPendingUsers')
          )}
          <br />
          {t('admin.dashboard.otherUsers', { passive: users.PASSIVE, rejected: users.REJECTED })}
        </StatCard>
        <StatCard
          label={t('admin.dashboard.feeds')}
          value={number.format(feeds.enabled)}
          unit={t('admin.dashboard.enabledFeeds')}
        >
          {feeds.failing > 0 || feeds.disabledAuto > 0 ? (
            <Link to="/admin/sources" className="font-medium text-destructive underline-offset-4 hover:underline">
              {[
                feeds.failing > 0 && t('admin.dashboard.failingFeeds', { count: feeds.failing }),
                feeds.disabledAuto > 0 && t('admin.dashboard.autoDisabledFeeds', { count: feeds.disabledAuto }),
              ]
                .filter(Boolean)
                .join(' · ')}
            </Link>
          ) : (
            t('admin.dashboard.noFailingFeeds')
          )}
        </StatCard>
        <StatCard
          label={t('admin.dashboard.searchIndex')}
          value={number.format(searchIndex.pendingOutboxEvents)}
          unit={t('admin.dashboard.pendingChanges')}
        >
          {searchIndex.pendingOutboxEvents === 0
            ? t('admin.dashboard.indexUpToDate')
            : t('admin.dashboard.indexCatchingUp')}
        </StatCard>
      </dl>

      <div className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <section aria-labelledby="dashboard-system">
          <h2 id="dashboard-system" className="border-b border-border pb-3 text-lg font-semibold">
            {t('admin.dashboard.system')}
          </h2>
          <ul className="divide-y divide-border">
            <ComponentRow name={t('admin.dashboard.components.database')} status={components.database} />
            <ComponentRow name={t('admin.dashboard.components.elasticsearch')} status={components.elasticsearch} />
            <ComponentRow name={t('admin.dashboard.components.objectStorage')} status={components.objectStorage} />
            <ComponentRow
              name={t('admin.dashboard.components.worker')}
              status={isWorkerStale ? 'DOWN' : 'UP'}
              text={
                workerActivity === null
                  ? t('admin.dashboard.workerNever')
                  : t('admin.dashboard.workerLastActivity', { time: formatPublishedAt(workerActivity, locale) })
              }
            />
          </ul>
        </section>

        <section aria-labelledby="dashboard-sources">
          <h2 id="dashboard-sources" className="border-b border-border pb-3 text-lg font-semibold">
            {t('admin.dashboard.sources')}
          </h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-xs text-muted-foreground">
                <th scope="col" className="py-2.5 text-left font-medium">
                  {t('admin.dashboard.source')}
                </th>
                <th scope="col" className="py-2.5 text-right font-medium">
                  {t('admin.dashboard.total')}
                </th>
                <th scope="col" className="py-2.5 text-right font-medium">
                  {t('admin.dashboard.last24h')}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {articles.bySource.map((source) => (
                <tr key={source.code}>
                  <th scope="row" className="py-2.5 text-left font-normal">
                    {source.name}
                  </th>
                  <td className="py-2.5 text-right tabular-nums">{number.format(source.total)}</td>
                  <td className="py-2.5 text-right text-muted-foreground tabular-nums">
                    {number.format(source.last24h)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </>
  )
}

interface StatCardProps {
  label: string
  value: string
  /** Sayının yanında küçük yazılan birim ("aktif"). */
  unit?: string
  /** Sayının altındaki kısa açıklama. */
  children: ReactNode
}

/** Bir özet: başlık, büyük sayı ve altında kısa açıklama. */
function StatCard({ label, value, unit, children }: StatCardProps) {
  return (
    <div className="flex flex-col bg-card p-5">
      <dt className="text-xs font-medium tracking-wide text-muted-foreground uppercase">{label}</dt>
      <dd className="mt-2 flex items-baseline gap-1.5">
        <span className="font-heading text-3xl font-semibold tabular-nums">{value}</span>
        {unit && <span className="text-sm text-muted-foreground">{unit}</span>}
      </dd>
      <dd className="mt-2 text-sm leading-relaxed text-muted-foreground">{children}</dd>
    </div>
  )
}

interface ComponentRowProps {
  name: string
  status: ComponentStatus
  /** Durumun yerine yazılacak metin (işçi için son etkinlik zamanı). */
  text?: string
}

/** Sistem durumunun bir satırı. Durum yalnızca renkle değil, yazıyla da söylenir (WCAG 1.4.1). */
function ComponentRow({ name, status, text }: ComponentRowProps) {
  const { t } = useTranslation()
  const isUp = status === 'UP'
  return (
    <li className="flex items-center justify-between gap-4 py-3 text-sm">
      <span className="flex items-center gap-2.5">
        <span aria-hidden className={cn('size-2 rounded-full', isUp ? 'bg-success' : 'bg-destructive')} />
        {name}
      </span>
      <span className={cn('text-right', isUp ? 'text-muted-foreground' : 'font-medium text-destructive')}>
        {text ?? (isUp ? t('admin.dashboard.up') : t('admin.dashboard.down'))}
      </span>
    </li>
  )
}

/** "22:15" gibi saat, Türkiye saatiyle. */
function formatClock(timestamp: number, locale: string): string {
  return new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit', timeZone: TIME_ZONE }).format(timestamp)
}
