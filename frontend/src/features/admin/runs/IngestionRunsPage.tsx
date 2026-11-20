import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { cn } from 'cn'
import type { Key } from 'react-aria-components'
import { useLocale } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router'
import { z } from 'zod'
import { fetchIngestionRuns, fetchSources, type IngestionRun } from '../../../api/adminSources'
import { useAccessToken } from '../../../auth/accessToken'
import { Button } from '../../../components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select'
import { formatDateTime } from '../../../lib/time'
import { Pagination } from '../../search/Pagination'

const STATUSES = ['RUNNING', 'SUCCEEDED', 'NOT_MODIFIED', 'FAILED'] as const

/** Filtre seçimlerinde "hepsi" seçeneğinin kimliği; adrese yazılmaz. */
const ALL = 'ALL'

/**
 * Adresteki durum (`/admin/ingestion-runs?sourceId=...&status=FAILED&page=2`). Bozuk değer API'ye
 * gönderilmez, varsayılanına döner (arama ekranıyla aynı kural).
 */
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

const stateSchema = z.object({
  sourceId: z.string().regex(UUID).optional().catch(undefined),
  status: z.enum(STATUSES).optional().catch(undefined),
  page: z.coerce.number().int().min(1).catch(1),
})

type RunsState = z.infer<typeof stateSchema>

function toUrlParams(state: RunsState): URLSearchParams {
  const params = new URLSearchParams()
  if (state.sourceId) params.set('sourceId', state.sourceId)
  if (state.status) params.set('status', state.status)
  if (state.page > 1) params.set('page', String(state.page))
  return params
}

/**
 * Yönetim paneli: toplama geçmişi (ekran akışları 5.2; FG-YP-05). Her okumanın zamanı (Türkiye saati),
 * kaynağı ve beslemesi, zamanlanmış mı elle mi başlatıldığı, sonucu ve haber sayıları; en yeniden eskiye.
 */
export function IngestionRunsPage() {
  const { t } = useTranslation()
  const accessToken = useAccessToken()
  const [params, setParams] = useSearchParams()
  const state = stateSchema.parse({
    sourceId: params.get('sourceId') ?? undefined,
    status: params.get('status') ?? undefined,
    page: params.get('page') ?? 1,
  })
  const update = (changes: Partial<RunsState>) => setParams(toUrlParams({ ...state, page: 1, ...changes }))
  const hrefForPage = (page: number) => `?${toUrlParams({ ...state, page }).toString()}`

  const apiQuery = toUrlParams({ ...state, page: 1 })
  apiQuery.set('page', String(state.page - 1))
  const query = apiQuery.toString()
  const runs = useQuery({
    queryKey: ['admin-ingestion-runs', query],
    queryFn: () => fetchIngestionRuns(accessToken, new URLSearchParams(query)),
    placeholderData: keepPreviousData,
  })
  const sources = useQuery({ queryKey: ['admin-sources'], queryFn: () => fetchSources(accessToken) })

  return (
    <div>
      <h1 className="mb-5 text-3xl font-semibold tracking-tight">{t('admin.runs.title')}</h1>
      <div className="flex flex-wrap gap-2">
        <Select
          aria-label={t('admin.runs.sourceFilter')}
          value={state.sourceId ?? ALL}
          onChange={(key: Key | null) => update({ sourceId: key === null || key === ALL ? undefined : String(key) })}
        >
          <SelectTrigger className={cn('w-auto', state.sourceId && 'border-primary text-primary')}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem id={ALL}>{t('admin.runs.allSources')}</SelectItem>
            {(sources.data?.items ?? []).map((source) => (
              <SelectItem key={source.id} id={source.id}>
                {source.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          aria-label={t('admin.runs.statusFilter')}
          value={state.status ?? ALL}
          onChange={(key: Key | null) => update({ status: STATUSES.find((status) => status === key) })}
        >
          <SelectTrigger className={cn('w-auto', state.status && 'border-primary text-primary')}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem id={ALL}>{t('admin.runs.allStatuses')}</SelectItem>
            {STATUSES.map((status) => (
              <SelectItem key={status} id={status}>
                {t(`admin.runs.status.${status}`)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {runs.isPending ? (
        <p className="mt-8 text-muted-foreground">{t('admin.runs.loading')}</p>
      ) : runs.isError ? (
        <div role="alert" className="mt-8">
          <p>{t('admin.runs.loadFailed')}</p>
          <Button variant="outline" className="mt-4" onPress={() => void runs.refetch()}>
            {t('admin.retry')}
          </Button>
        </div>
      ) : runs.data.items.length === 0 ? (
        <p className="py-16 text-center text-muted-foreground">{t('admin.runs.empty')}</p>
      ) : (
        <>
          <ul
            aria-busy={runs.isFetching}
            className={cn(
              'mt-6 divide-y divide-border border-t border-border transition-opacity',
              runs.isPlaceholderData && 'opacity-50',
            )}
          >
            {runs.data.items.map((run) => (
              <li key={run.id}>
                <RunRow run={run} />
              </li>
            ))}
          </ul>
          <Pagination page={state.page} totalPages={runs.data.totalPages} hrefForPage={hrefForPage} />
        </>
      )}
    </div>
  )
}

function RunRow({ run }: { run: IngestionRun }) {
  const { t } = useTranslation()
  const { locale } = useLocale()

  return (
    <div className="flex flex-wrap items-start gap-x-6 gap-y-1 py-3 text-sm">
      <time dateTime={run.startedAt} className="w-40 text-xs text-muted-foreground tabular-nums">
        {formatDateTime(run.startedAt, locale)}
      </time>
      <div className="min-w-0 flex-1 basis-56">
        <p>
          <span className="font-medium">{run.sourceName}</span> · {run.feedName}
        </p>
        {run.errorMessage && <p className="text-xs text-destructive">{run.errorMessage}</p>}
      </div>
      <p className="w-28 text-xs text-muted-foreground">{t(`admin.runs.trigger.${run.trigger}`)}</p>
      <div className="w-48 text-xs">
        <p className={cn('font-medium', run.status === 'FAILED' && 'text-destructive')}>
          {t(`admin.runs.status.${run.status}`)}
          {run.httpStatus !== null && ` (HTTP ${run.httpStatus})`}
        </p>
        {run.itemsReceived !== null && (
          <p className="text-muted-foreground">
            {t('admin.runs.counts', {
              newCount: run.itemsNew ?? 0,
              duplicate: run.itemsDuplicate ?? 0,
              failed: run.itemsFailed ?? 0,
            })}
          </p>
        )}
      </div>
    </div>
  )
}
