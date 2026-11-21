import { apiDownload, apiGet, type DownloadedFile } from './client'

/** Audit kaydının hedef türleri (veri modeli 3.13). */
export const AUDIT_TARGET_TYPES = ['USER', 'SOURCE', 'FEED'] as const
export type AuditTargetType = (typeof AUDIT_TARGET_TYPES)[number]

export const AUDIT_RESULTS = ['SUCCESS', 'FAILURE'] as const
export type AuditResult = (typeof AUDIT_RESULTS)[number]

/** Yönetim panelindeki bir audit kaydı (API sözleşmesi 6.8). */
export interface AuditEvent {
  id: string
  occurredAt: string
  actorType: 'USER' | 'SYSTEM'
  /** Sistem kaydında (işçi) `null`. */
  actorUserId: string | null
  actorEmail: string | null
  action: string
  targetType: string | null
  targetId: string | null
  result: AuditResult
  requestId: string | null
  ipAddress: string | null
  /** İşleme özgü alanlar; yoksa boş nesne. */
  details: Record<string, unknown>
}

export interface AuditEventsResponse {
  items: AuditEvent[]
  page: number
  size: number
  totalElements: number
  totalPages: number
}

const AUDIT_EVENTS = '/api/v1/admin/audit-events'

export function fetchAuditEvents(accessToken: string, query: URLSearchParams): Promise<AuditEventsResponse> {
  return apiGet<AuditEventsResponse>(AUDIT_EVENTS, accessToken, query)
}

/** Aynı filtrelerle CSV dosyası; 100.000'den fazla kayıtta `EXPORT_TOO_LARGE` hatası. */
export function exportAuditEvents(accessToken: string, query: URLSearchParams): Promise<DownloadedFile> {
  return apiDownload(`${AUDIT_EVENTS}/export`, accessToken, query)
}
