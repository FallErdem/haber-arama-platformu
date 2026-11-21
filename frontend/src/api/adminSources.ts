import { apiGet, apiSendJson } from './client'

/** Kaynaklar listesindeki bir kaynak ve sağlık özeti (API sözleşmesi 6.2). */
export interface SourceOverview {
  id: string
  code: string
  name: string
  readerType: string
  language: string
  enabled: boolean
  feedCount: number
  /** Etkin olup son okuması başarısız olan ve kendiliğinden kapanmış besleme sayısı. */
  failingFeedCount: number
  lastSuccessAt: string | null
  purgeRequestedAt: string | null
}

/** `MANUAL`: yönetici kapattı; `AUTO`: art arda hatalar yüzünden kendiliğinden kapandı. */
export type DisabledReason = 'MANUAL' | 'AUTO'

/** Yönetim panelindeki bir besleme: ayarları ve sağlık durumu (API sözleşmesi 6.3). */
export interface ManagedFeed {
  id: string
  sourceId: string
  name: string
  url: string
  defaultCategoryCode: string | null
  useItemCategories: boolean
  fetchIntervalMinutes: number
  enabled: boolean
  disabledReason: DisabledReason | null
  consecutiveFailures: number
  lastSuccessAt: string | null
  lastError: string | null
  nextFetchAt: string
  manualFetchRequestedAt: string | null
  version: number
}

/** Yönetim panelindeki bir kaynak: ayarları ve beslemeleri (API sözleşmesi 6.2). */
export interface ManagedSource {
  id: string
  code: string
  name: string
  homepageUrl: string
  readerType: string
  language: string
  requestIntervalSeconds: number
  dailyRequestLimit: number | null
  license: string | null
  attributionText: string | null
  feedTimeZone: string | null
  enabled: boolean
  /** İçeriğin silinmesi istendiyse istenme zamanı; işçi silmeyi bitirince `null` olur. */
  purgeRequestedAt: string | null
  version: number
  /** Kaynağın haber sayısı (gizlenenler dahil); içerik silinince 0 olur. */
  articleCount: number
  feeds: ManagedFeed[]
}

export interface NewSource {
  code: string
  name: string
  homepageUrl: string
  readerType: 'RSS' | 'ATOM'
  language: 'tr' | 'en'
  requestIntervalSeconds: number
}

/**
 * Kaynak değişikliği: yalnızca gönderilen alanlar değişir (sözleşme 2.5). Boş bırakılabilen alanlar için
 * `null` gönderilirse alan boşaltılır.
 */
export interface SourceChange {
  name?: string
  homepageUrl?: string
  requestIntervalSeconds?: number
  dailyRequestLimit?: number | null
  license?: string | null
  attributionText?: string | null
  feedTimeZone?: string | null
  enabled?: boolean
  version: number
}

export interface FeedSettings {
  name: string
  url: string
  defaultCategoryCode: string | null
  useItemCategories: boolean
  fetchIntervalMinutes: number
}

export type FeedChange = Partial<FeedSettings> & { enabled?: boolean; version: number }

/** Toplama geçmişindeki bir okuma (API sözleşmesi 6.5). */
export interface IngestionRun {
  id: string
  feedId: string
  feedName: string
  sourceId: string
  sourceCode: string
  sourceName: string
  trigger: 'SCHEDULED' | 'MANUAL'
  status: 'RUNNING' | 'SUCCEEDED' | 'NOT_MODIFIED' | 'FAILED'
  startedAt: string
  finishedAt: string | null
  httpStatus: number | null
  itemsReceived: number | null
  itemsNew: number | null
  itemsDuplicate: number | null
  itemsFailed: number | null
  errorMessage: string | null
}

export interface IngestionRunsResponse {
  items: IngestionRun[]
  page: number
  size: number
  totalElements: number
  totalPages: number
}

const SOURCES = '/api/v1/admin/sources'

export function fetchSources(accessToken: string): Promise<{ items: SourceOverview[] }> {
  return apiGet<{ items: SourceOverview[] }>(SOURCES, accessToken)
}

export function fetchSource(accessToken: string, sourceId: string): Promise<ManagedSource> {
  return apiGet<ManagedSource>(`${SOURCES}/${encodeURIComponent(sourceId)}`, accessToken)
}

export function createSource(accessToken: string, source: NewSource): Promise<ManagedSource> {
  return apiSendJson<ManagedSource>('POST', SOURCES, accessToken, source)
}

export function updateSource(accessToken: string, sourceId: string, change: SourceChange): Promise<ManagedSource> {
  return apiSendJson<ManagedSource>('PATCH', `${SOURCES}/${encodeURIComponent(sourceId)}`, accessToken, change)
}

/** Elle toplama (FG-YP-08); okumayı işçi yapar. Yanıt: okunacak besleme sayısı. */
export function requestFetch(accessToken: string, sourceId: string): Promise<{ feedCount: number }> {
  return apiSendJson<{ feedCount: number }>('POST', `${SOURCES}/${encodeURIComponent(sourceId)}/fetch`, accessToken)
}

/**
 * Kaynağın bütün içeriğinin silinmesini ister (FG-YP-14); silmeyi işçi yapar. Onay olarak kaynağın kodu
 * gönderilir. Yanıt: silinecek haber sayısı.
 */
export function requestPurge(
  accessToken: string,
  sourceId: string,
  confirmationCode: string,
): Promise<{ articleCount: number }> {
  return apiSendJson<{ articleCount: number }>(
    'POST',
    `${SOURCES}/${encodeURIComponent(sourceId)}/purge`,
    accessToken,
    { confirmationCode },
  )
}

export function createFeed(accessToken: string, sourceId: string, feed: FeedSettings): Promise<ManagedFeed> {
  return apiSendJson<ManagedFeed>('POST', `${SOURCES}/${encodeURIComponent(sourceId)}/feeds`, accessToken, feed)
}

export function updateFeed(accessToken: string, feedId: string, change: FeedChange): Promise<ManagedFeed> {
  return apiSendJson<ManagedFeed>('PATCH', `/api/v1/admin/feeds/${encodeURIComponent(feedId)}`, accessToken, change)
}

/** Toplama geçmişi. `query`: `sourceId`, `feedId`, `status`, `page` (0'dan başlar). */
export function fetchIngestionRuns(accessToken: string, query: URLSearchParams): Promise<IngestionRunsResponse> {
  return apiGet<IngestionRunsResponse>('/api/v1/admin/ingestion-runs', accessToken, query)
}
