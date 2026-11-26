import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { cn } from 'cn'
import { ExternalLinkIcon } from 'lucide-react'
import { useState } from 'react'
import type { Key } from 'react-aria-components'
import { useLocale } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router'
import { z } from 'zod'
import { fetchAdminArticles, unhideArticle, type AdminArticle } from '../../../api/adminArticles'
import { fetchSources } from '../../../api/adminSources'
import { useAccessToken } from '../../../auth/accessToken'
import { ListSkeleton } from '../../../components/ListSkeleton'
import { Button } from '../../../components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select'
import { endOfDay, formatDateTime, isIsoDay, startOfDay } from '../../../lib/time'
import { DateRangeFilter } from '../../search/DateRangeFilter'
import { Pagination } from '../../search/Pagination'
import { adminErrorMessage, isStaleError } from '../adminErrors'

/** Filtre seçimlerinde "hepsi" seçeneğinin kimliği; adrese yazılmaz. */
const ALL = 'ALL'

/**
 * Adresteki durum (`/admin/hidden-articles?source=TRT&from=2026-11-01&to=2026-11-20&page=2`). Bozuk değer
 * API'ye gönderilmez, varsayılanına döner.
 */
const isoDay = z.string().refine(isIsoDay).optional().catch(undefined)
const stateSchema = z.object({
  source: z
    .string()
    .regex(/^[A-Z][A-Z0-9_]{1,39}$/)
    .optional()
    .catch(undefined),
  from: isoDay,
  to: isoDay,
  page: z.coerce.number().int().min(1).catch(1),
})

type HiddenState = z.infer<typeof stateSchema>

function toUrlParams(state: HiddenState): URLSearchParams {
  const params = new URLSearchParams()
  if (state.source) params.set('source', state.source)
  if (state.from) params.set('from', state.from)
  if (state.to) params.set('to', state.to)
  if (state.page > 1) params.set('page', String(state.page))
  return params
}

/** API parametreleri: yalnızca gizliler; günler Türkiye saatinin UTC anlarına çevrilir; sayfa 0'dan başlar. */
function toApiParams(state: HiddenState): URLSearchParams {
  const params = new URLSearchParams({ hidden: 'true' })
  if (state.source) params.set('sources', state.source)
  if (state.from) params.set('from', startOfDay(state.from).toISOString())
  if (state.to) params.set('to', endOfDay(state.to).toISOString())
  params.set('page', String(state.page - 1))
  return params
}

/**
 * Yönetim paneli: gizlenen haberler (ekran akışları, "Gizlenen haberler"; FG-YP-09). En son gizlenen önce;
 * her haberin gerekçesi, gizleyen yönetici ve zamanı. "Gizlemeyi geri al" haberi aramaya döndürür.
 */
export function HiddenArticlesPage() {
  const { t } = useTranslation()
  const accessToken = useAccessToken()
  const [params, setParams] = useSearchParams()
  const [notice, setNotice] = useState<{ kind: 'success' | 'error'; text: string } | null>(null)
  const parsed = stateSchema.parse({
    source: params.get('source') ?? undefined,
    from: params.get('from') ?? undefined,
    to: params.get('to') ?? undefined,
    page: params.get('page') ?? 1,
  })
  // Başlangıcı bitişinden sonra olan aralık yok sayılır (API de reddeder).
  const state: HiddenState =
    parsed.from && parsed.to && parsed.from > parsed.to ? { ...parsed, from: undefined, to: undefined } : parsed

  const update = (changes: Partial<HiddenState>) => setParams(toUrlParams({ ...state, page: 1, ...changes }))
  const hrefForPage = (page: number) => `?${toUrlParams({ ...state, page }).toString()}`

  const query = toApiParams(state).toString()
  const articles = useQuery({
    queryKey: ['admin-hidden-articles', query],
    queryFn: () => fetchAdminArticles(accessToken, new URLSearchParams(query)),
    placeholderData: keepPreviousData,
  })
  const sources = useQuery({ queryKey: ['admin-sources'], queryFn: () => fetchSources(accessToken) })

  return (
    <div>
      <h1 className="mb-5 text-3xl font-semibold tracking-tight">{t('admin.hidden.title')}</h1>
      <div className="flex flex-wrap gap-2">
        <Select
          aria-label={t('admin.hidden.sourceFilter')}
          value={state.source ?? ALL}
          onChange={(key: Key | null) => update({ source: key === null || key === ALL ? undefined : String(key) })}
        >
          <SelectTrigger className={cn('w-auto', state.source && 'border-primary text-primary')}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem id={ALL}>{t('admin.hidden.allSources')}</SelectItem>
            {(sources.data?.items ?? []).map((source) => (
              <SelectItem key={source.code} id={source.code}>
                {source.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <DateRangeFilter
          from={state.from}
          to={state.to}
          onChange={(from, to) => update({ from, to })}
          emptyLabel={t('admin.hidden.anyDate')}
        />
      </div>

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

      {articles.isPending ? (
        <ListSkeleton label={t('admin.hidden.loading')} className="mt-6" />
      ) : articles.isError ? (
        <div role="alert" className="mt-8">
          <p>{t('admin.hidden.loadFailed')}</p>
          <Button variant="outline" className="mt-4" onPress={() => void articles.refetch()}>
            {t('admin.retry')}
          </Button>
        </div>
      ) : articles.data.items.length === 0 ? (
        <p className="py-16 text-center text-muted-foreground">{t('admin.hidden.empty')}</p>
      ) : (
        <>
          <ul
            aria-busy={articles.isFetching}
            className={cn(
              'mt-6 divide-y divide-border border-t border-border transition-opacity',
              articles.isPlaceholderData && 'opacity-50',
            )}
          >
            {articles.data.items.map((article) => (
              <li key={article.id} className="transition-colors hover:bg-muted/40">
                <HiddenArticleRow article={article} onNotice={setNotice} />
              </li>
            ))}
          </ul>
          <Pagination page={state.page} totalPages={articles.data.totalPages} hrefForPage={hrefForPage} />
        </>
      )}
    </div>
  )
}

interface HiddenArticleRowProps {
  article: AdminArticle
  onNotice: (notice: { kind: 'success' | 'error'; text: string }) => void
}

/** Bir gizli haber: kaynağı, başlığı, gerekçesi, gizleyen ve zamanı; "Gizlemeyi geri al". */
function HiddenArticleRow({ article, onNotice }: HiddenArticleRowProps) {
  const { t } = useTranslation()
  const { locale } = useLocale()
  const accessToken = useAccessToken()
  const queryClient = useQueryClient()
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['admin-hidden-articles'] })

  const unhide = useMutation({
    mutationFn: () => unhideArticle(accessToken, article.id),
    onSuccess: async () => {
      onNotice({ kind: 'success', text: t('admin.hidden.unhidden', { title: article.title }) })
      // Arama ve Kaydedilenler de yeniden istenir: haber yeniden görünür.
      void queryClient.invalidateQueries({ queryKey: ['articles'] })
      void queryClient.invalidateQueries({ queryKey: ['saved-articles'] })
      await refresh()
    },
    onError: (error) => {
      onNotice({ kind: 'error', text: adminErrorMessage(error, t) })
      if (isStaleError(error)) void refresh()
    },
  })

  return (
    <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3 py-4">
      <div className="min-w-0 flex-1 basis-80">
        <p className="text-xs text-muted-foreground">
          <span className="font-medium tracking-wide uppercase">{article.sourceName}</span>
          <span aria-hidden> · </span>
          <time dateTime={article.publishedAt}>{formatDateTime(article.publishedAt, locale)}</time>
        </p>
        {/* Detay sayfası gizli haberi göstermez; haber kaynağında açılır. */}
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-1 inline-flex items-start gap-1.5 font-heading text-lg leading-snug font-semibold hover:underline"
        >
          {article.title}
          <ExternalLinkIcon aria-label={t('admin.hidden.openOriginal')} className="mt-1 size-3.5 shrink-0" />
        </a>
        {article.hiddenReason && (
          <blockquote className="mt-2 border-l-2 border-border pl-3 text-sm">{article.hiddenReason}</blockquote>
        )}
        {article.hiddenAt && (
          <p className="mt-2 text-xs text-muted-foreground">
            {t('admin.hidden.hiddenBy', {
              admin: article.hiddenByEmail ?? '—',
              time: formatDateTime(article.hiddenAt, locale),
            })}
          </p>
        )}
      </div>
      {/* Erişilebilir ada haberin başlığı eklenir: listede aynı adlı düğmeler ayırt edilsin (WCAG 2.5.3). */}
      <Button
        variant="outline"
        size="sm"
        aria-label={t('admin.hidden.unhideFor', { title: article.title })}
        isDisabled={unhide.isPending}
        onPress={() => unhide.mutate()}
      >
        {t('admin.hidden.unhide')}
      </Button>
    </div>
  )
}
