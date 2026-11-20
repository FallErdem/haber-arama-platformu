import type { TFunction } from 'i18next'
import { ApiError } from '../../api/client'

/** Yönetim işlemlerinin hata kodları; her birinin kendi mesajı vardır. */
const KNOWN_CODES = [
  'VERSION_CONFLICT',
  'ALREADY_EXISTS',
  'INVALID_STATE_TRANSITION',
  'LAST_ACTIVE_ADMIN',
  'VALIDATION_FAILED',
]

/**
 * Bir yönetim işleminin hatasını kullanıcıya gösterilecek metne çevirir. Metin koddan seçilir
 * (FOG-27); tanınmayan hatada genel mesaj gösterilir.
 */
export function adminErrorMessage(error: unknown, t: TFunction): string {
  const code = error instanceof ApiError ? error.code : undefined
  return code && KNOWN_CODES.includes(code) ? t(`admin.errors.${code}`) : t('admin.errors.failed')
}

/** Kaydın bu arada değiştiğini söyleyen hatalar: ekrandaki veri yenilenmeli. */
export function isStaleError(error: unknown): boolean {
  return error instanceof ApiError && (error.code === 'VERSION_CONFLICT' || error.code === 'INVALID_STATE_TRANSITION')
}

/** API'nin geçersiz bulduğu alanlar; formlar bu alanları işaretler. */
export function invalidFields(error: unknown): string[] {
  return error instanceof ApiError ? error.fields : []
}
