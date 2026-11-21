import { z } from 'zod'
import { AUDIT_RESULTS, AUDIT_TARGET_TYPES, type AuditResult, type AuditTargetType } from '../../../api/adminAudit'
import { endOfDay, isIsoDay, startOfDay } from '../../../lib/time'

/**
 * Audit kayıtları ekranının durumu adres çubuğunda tutulur (arama ekranıyla aynı kural): sayfa yenilenince
 * ve geri düğmesinde filtreler korunur. Örnek:
 *
 *   /admin/audit-events?action=USER_APPROVED&result=FAILURE&from=2026-11-01&to=2026-11-05&page=2
 *
 * Adresteki bozuk bir değer API'ye gönderilmez, varsayılanına döner.
 */

/** Ekranda seçilebilen işlem kodları (veri modeli 3.13); sırası seçim kutusundaki sıradır. */
export const AUDIT_ACTIONS = [
  'USER_REGISTERED',
  'SESSION_STARTED',
  'ACCESS_DENIED',
  'USER_APPROVED',
  'USER_REJECTED',
  'USER_ROLE_CHANGED',
  'USER_STATUS_CHANGED',
  'SOURCE_CREATED',
  'SOURCE_UPDATED',
  'SOURCE_ENABLED',
  'SOURCE_DISABLED',
  'FETCH_REQUESTED',
  'FEED_CREATED',
  'FEED_UPDATED',
  'FEED_ENABLED',
  'FEED_DISABLED',
  'FEED_AUTO_DISABLED',
  'AUDIT_EXPORTED',
] as const

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export interface AuditState {
  /** Bir kullanıcının kayıtları: listedeki kullanıcıya tıklanınca seçilir. */
  actorUserId: string | undefined
  action: string | undefined
  targetType: AuditTargetType | undefined
  /** Bir nesnenin kayıtları: listedeki hedefe tıklanınca türüyle birlikte seçilir. */
  targetId: string | undefined
  result: AuditResult | undefined
  /** Aralığın günleri (`2026-11-05`), Türkiye saatiyle; ikisi de yoksa API son 30 günü verir. */
  from: string | undefined
  to: string | undefined
  /** Adreste 1'den başlar; API'de 0'dan. */
  page: number
}

const uuid = z.string().regex(UUID).optional().catch(undefined)
const isoDay = z.string().refine(isIsoDay).optional().catch(undefined)

const schema = z.object({
  actorUserId: uuid,
  // İşçinin kodları ve ileride eklenecekler de aranabilsin diye listeyle değil, biçimle denetlenir (API ile aynı).
  action: z
    .string()
    .regex(/^[A-Z][A-Z_]{0,63}$/)
    .optional()
    .catch(undefined),
  targetType: z.enum(AUDIT_TARGET_TYPES).optional().catch(undefined),
  targetId: uuid,
  result: z.enum(AUDIT_RESULTS).optional().catch(undefined),
  from: isoDay,
  to: isoDay,
  page: z.coerce.number().int().min(1).catch(1),
})

export function parseAuditState(params: URLSearchParams): AuditState {
  const parsed = schema.parse({
    actorUserId: params.get('actorUserId') ?? undefined,
    action: params.get('action') ?? undefined,
    targetType: params.get('targetType') ?? undefined,
    targetId: params.get('targetId') ?? undefined,
    result: params.get('result') ?? undefined,
    from: params.get('from') ?? undefined,
    to: params.get('to') ?? undefined,
    page: params.get('page') ?? 1,
  })
  // Başlangıcı bitişinden sonra olan aralık anlamsızdır; API de reddeder. Aralık yok sayılır.
  const isRangeValid = parsed.from === undefined || parsed.to === undefined || parsed.from <= parsed.to
  return {
    actorUserId: parsed.actorUserId,
    action: parsed.action,
    targetType: parsed.targetType,
    targetId: parsed.targetId,
    result: parsed.result,
    from: isRangeValid ? parsed.from : undefined,
    to: isRangeValid ? parsed.to : undefined,
    page: parsed.page,
  }
}

/** Varsayılan değerler adrese yazılmaz: aynı durum her zaman aynı adresi üretir. */
export function toUrlParams(state: AuditState): URLSearchParams {
  const params = filterParams(state)
  if (state.from) params.set('from', state.from)
  if (state.to) params.set('to', state.to)
  if (state.page > 1) params.set('page', String(state.page))
  return params
}

/**
 * Durumu API parametrelerine çevirir (API sözleşmesi 6.8). Adresten farkı: tarih aralığı Türkiye
 * saatindeki günlerin UTC'deki başlangıç ve bitiş anlarıdır. Dışa aktarma aynı filtreleri sayfasız alır.
 */
export function toApiParams(state: AuditState, options: { paged: boolean }): URLSearchParams {
  const params = filterParams(state)
  if (state.from) params.set('from', startOfDay(state.from).toISOString())
  if (state.to) params.set('to', endOfDay(state.to).toISOString())
  if (options.paged) params.set('page', String(state.page - 1))
  return params
}

function filterParams(state: AuditState): URLSearchParams {
  const params = new URLSearchParams()
  if (state.actorUserId) params.set('actorUserId', state.actorUserId)
  if (state.action) params.set('action', state.action)
  if (state.targetType) params.set('targetType', state.targetType)
  if (state.targetId) params.set('targetId', state.targetId)
  if (state.result) params.set('result', state.result)
  return params
}
