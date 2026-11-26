import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query'
import { cn } from 'cn'
import { DownloadIcon, XIcon } from 'lucide-react'
import { useId, useState } from 'react'
import type { Key } from 'react-aria-components'
import { useLocale } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router'
import {
  AUDIT_RESULTS,
  AUDIT_TARGET_TYPES,
  type AuditEvent,
  exportAuditEvents,
  fetchAuditEvents,
} from '../../../api/adminAudit'
import { ApiError } from '../../../api/client'
import { useAccessToken } from '../../../auth/accessToken'
import { ListSkeleton } from '../../../components/ListSkeleton'
import { Button } from '../../../components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select'
import { saveFile } from '../../../lib/download'
import { formatDateTime } from '../../../lib/time'
import { DateRangeFilter } from '../../search/DateRangeFilter'
import { Pagination } from '../../search/Pagination'
import { AUDIT_ACTIONS, type AuditState, parseAuditState, toApiParams, toUrlParams } from './auditState'

/** Filtre seçimlerinde "hepsi" seçeneğinin kimliği; adrese yazılmaz. */
const ALL = 'ALL'

/** Uzun kimliğin kısa gösterimi. UUIDv7'nin başı zamandır, aynı anda oluşanlarda aynıdır; sonu rastgeledir. */
function shortId(id: string): string {
  return `…${id.slice(-8)}`
}

/**
 * Yönetim paneli: audit kayıtları (ekran akışları, "Audit kayıtları"; FG-YP-10, FG-YP-11). İşlem, hedef
 * türü, sonuç ve tarih filtreleri; tarih seçilmezse son 30 gün. Listedeki bir kullanıcıya veya hedefe
 * tıklanınca liste onun kayıtlarına süzülür. Filtrelenmiş kayıtlar CSV olarak indirilebilir.
 */
export function AuditEventsPage() {
  const { t } = useTranslation()
  const accessToken = useAccessToken()
  const [params, setParams] = useSearchParams()
  const state = parseAuditState(params)

  const query = toApiParams(state, { paged: true }).toString()
  const events = useQuery({
    queryKey: ['admin-audit-events', query],
    queryFn: () => fetchAuditEvents(accessToken, new URLSearchParams(query)),
    placeholderData: keepPreviousData,
  })
  const exportCsv = useMutation({
    mutationFn: () => exportAuditEvents(accessToken, toApiParams(state, { paged: false })),
    onSuccess: ({ blob, filename }) => saveFile(blob, filename ?? 'audit-events.csv'),
  })

  const update = (changes: Partial<AuditState>) => {
    // Filtre değişince eski dışa aktarma hatası artık geçerli değildir.
    exportCsv.reset()
    setParams(toUrlParams({ ...state, page: 1, ...changes }))
  }
  const hrefForPage = (page: number) => `?${toUrlParams({ ...state, page }).toString()}`

  // Seçili kullanıcının e-postası adreste yoktur; listedeki kayıtlarından alınır.
  const actorEmail = events.data?.items.find((event) => event.actorUserId === state.actorUserId)?.actorEmail
  const actorName = state.actorUserId ? (actorEmail ?? shortId(state.actorUserId)) : undefined
  const targetName = state.targetId
    ? `${state.targetType ? t(`admin.audit.targetTypes.${state.targetType}`) : ''} ${shortId(state.targetId)}`.trim()
    : undefined

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-semibold tracking-tight">{t('admin.audit.title')}</h1>
        <Button variant="outline" isPending={exportCsv.isPending} onPress={() => exportCsv.mutate()}>
          <DownloadIcon aria-hidden />
          {exportCsv.isPending ? t('admin.audit.exporting') : t('admin.audit.export')}
        </Button>
      </div>

      {exportCsv.isError && (
        <p role="alert" className="mb-4 text-sm text-destructive">
          {exportCsv.error instanceof ApiError && exportCsv.error.code === 'EXPORT_TOO_LARGE'
            ? t('admin.audit.exportTooLarge')
            : t('admin.audit.exportFailed')}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        <Select
          aria-label={t('admin.audit.actionFilter')}
          value={state.action ?? ALL}
          onChange={(key: Key | null) => update({ action: key === null || key === ALL ? undefined : String(key) })}
        >
          <SelectTrigger className={cn('w-auto', state.action && 'border-primary text-primary')}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem id={ALL}>{t('admin.audit.allActions')}</SelectItem>
            {AUDIT_ACTIONS.map((action) => (
              <SelectItem key={action} id={action}>
                {t(`admin.audit.actions.${action}`)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          aria-label={t('admin.audit.targetTypeFilter')}
          value={state.targetType ?? ALL}
          onChange={(key: Key | null) =>
            // Hedef türü değişince seçili hedef artık o türden olmayabilir; bırakılır.
            update({ targetType: AUDIT_TARGET_TYPES.find((type) => type === key), targetId: undefined })
          }
        >
          <SelectTrigger className={cn('w-auto', state.targetType && 'border-primary text-primary')}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem id={ALL}>{t('admin.audit.allTargetTypes')}</SelectItem>
            {AUDIT_TARGET_TYPES.map((type) => (
              <SelectItem key={type} id={type}>
                {t(`admin.audit.targetTypes.${type}`)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          aria-label={t('admin.audit.resultFilter')}
          value={state.result ?? ALL}
          onChange={(key: Key | null) => update({ result: AUDIT_RESULTS.find((result) => result === key) })}
        >
          <SelectTrigger className={cn('w-auto', state.result && 'border-primary text-primary')}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem id={ALL}>{t('admin.audit.allResults')}</SelectItem>
            {AUDIT_RESULTS.map((result) => (
              <SelectItem key={result} id={result}>
                {t(`admin.audit.results.${result}`)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <DateRangeFilter
          from={state.from}
          to={state.to}
          onChange={(from, to) => update({ from, to })}
          emptyLabel={t('admin.audit.lastThirtyDays')}
        />
      </div>

      {(actorName || targetName) && (
        <div className="mt-3 flex flex-wrap gap-2">
          {actorName && (
            <FilterChip
              label={t('admin.audit.actorFilter', { name: actorName })}
              onRemove={() => update({ actorUserId: undefined })}
            />
          )}
          {targetName && (
            <FilterChip
              label={t('admin.audit.targetFilter', { name: targetName })}
              onRemove={() => update({ targetType: undefined, targetId: undefined })}
            />
          )}
        </div>
      )}

      {events.isPending ? (
        <ListSkeleton label={t('admin.audit.loading')} className="mt-6" />
      ) : events.isError ? (
        <div role="alert" className="mt-8">
          <p>{t('admin.audit.loadFailed')}</p>
          <Button variant="outline" className="mt-4" onPress={() => void events.refetch()}>
            {t('admin.retry')}
          </Button>
        </div>
      ) : events.data.items.length === 0 ? (
        <p className="py-16 text-center text-muted-foreground">{t('admin.audit.empty')}</p>
      ) : (
        <>
          <ul
            aria-busy={events.isFetching}
            className={cn(
              'mt-6 divide-y divide-border border-t border-border transition-opacity',
              events.isPlaceholderData && 'opacity-50',
            )}
          >
            {events.data.items.map((event) => (
              <li key={event.id} className="transition-colors hover:bg-muted/40">
                <AuditEventRow
                  event={event}
                  onSelectActor={(actorUserId) => update({ actorUserId })}
                  onSelectTarget={(targetType, targetId) =>
                    update({ targetType: AUDIT_TARGET_TYPES.find((type) => type === targetType), targetId })
                  }
                />
              </li>
            ))}
          </ul>
          <Pagination page={state.page} totalPages={events.data.totalPages} hrefForPage={hrefForPage} />
        </>
      )}
    </div>
  )
}

/** Listedeki tıklamayla seçilmiş bir filtre; çarpı düğmesi kaldırır. */
function FilterChip({ label, onRemove }: { label: string; onRemove: () => void }) {
  const { t } = useTranslation()
  return (
    <Button
      variant="outline"
      size="sm"
      className="border-primary text-primary"
      aria-label={t('admin.audit.removeFilter', { name: label })}
      onPress={onRemove}
    >
      {label}
      <XIcon aria-hidden />
    </Button>
  )
}

interface AuditEventRowProps {
  event: AuditEvent
  onSelectActor: (actorUserId: string) => void
  onSelectTarget: (targetType: string, targetId: string) => void
}

/** Bir kayıt: zaman (Türkiye saati), işlem, kullanıcı, hedef, sonuç ve IP; "Ayrıntılar" geri kalanını açar. */
function AuditEventRow({ event, onSelectActor, onSelectTarget }: AuditEventRowProps) {
  const { t } = useTranslation()
  const { locale } = useLocale()
  const [open, setOpen] = useState(false)
  const detailsId = useId()

  const time = formatDateTime(event.occurredAt, locale)
  // İleride eklenen ve bu sürümün tanımadığı bir kod, kendi adıyla gösterilir.
  const action = t(`admin.audit.actions.${event.action}`, { defaultValue: event.action })
  const actorName = event.actorUserId ? (event.actorEmail ?? shortId(event.actorUserId)) : null
  const targetName =
    event.targetType && event.targetId
      ? `${t(`admin.audit.targetTypes.${event.targetType}`, { defaultValue: event.targetType })} ${shortId(event.targetId)}`
      : null
  const detailEntries = Object.entries(event.details)

  return (
    <div className="py-3 text-sm">
      <div className="flex flex-wrap items-start gap-x-6 gap-y-1">
        <time dateTime={event.occurredAt} className="w-40 text-xs text-muted-foreground tabular-nums">
          {time}
        </time>
        <div className="min-w-0 flex-1 basis-56">
          <p className="font-medium">{action}</p>
          {event.actorUserId && actorName ? (
            <Button
              variant="link"
              size="sm"
              className="h-auto p-0 text-xs"
              aria-label={t('admin.audit.showActorEvents', { name: actorName })}
              onPress={() => onSelectActor(event.actorUserId!)}
            >
              {actorName}
            </Button>
          ) : (
            <p className="text-xs text-muted-foreground">{t('admin.audit.system')}</p>
          )}
        </div>
        <div className="w-36 text-xs">
          {event.targetType && event.targetId && targetName ? (
            <Button
              variant="link"
              size="sm"
              className="h-auto p-0 text-xs"
              aria-label={t('admin.audit.showTargetEvents', { name: targetName })}
              onPress={() => onSelectTarget(event.targetType!, event.targetId!)}
            >
              {targetName}
            </Button>
          ) : (
            <span className="text-muted-foreground">—</span>
          )}
        </div>
        <p className={cn('w-20 text-xs font-medium', event.result === 'FAILURE' && 'text-destructive')}>
          {t(`admin.audit.results.${event.result}`)}
        </p>
        <p className="w-28 text-xs text-muted-foreground tabular-nums">{event.ipAddress ?? '—'}</p>
        <Button
          variant="ghost"
          size="sm"
          aria-expanded={open}
          aria-controls={detailsId}
          aria-label={t('admin.audit.detailsFor', { action, time })}
          onPress={() => setOpen((value) => !value)}
        >
          {t('admin.audit.details')}
        </Button>
      </div>
      <dl
        id={detailsId}
        hidden={!open}
        className="mt-2 grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1 rounded-md bg-muted px-3 py-2 text-xs"
      >
        <DetailItem label={t('admin.audit.fields.id')} value={event.id} />
        {event.requestId && <DetailItem label={t('admin.audit.fields.requestId')} value={event.requestId} />}
        {event.actorUserId && <DetailItem label={t('admin.audit.fields.actorUserId')} value={event.actorUserId} />}
        {event.targetId && <DetailItem label={t('admin.audit.fields.targetId')} value={event.targetId} />}
        {detailEntries.map(([key, value]) => (
          <DetailItem key={key} label={key} value={typeof value === 'string' ? value : JSON.stringify(value)} />
        ))}
      </dl>
    </div>
  )
}

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="break-all">{value}</dd>
    </>
  )
}
