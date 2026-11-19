import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import type { Key } from 'react-aria-components'
import { useLocale } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { approveUser, changeUser, rejectUser, type AdminUser, type UserChange } from '../../../api/adminUsers'
import { ApiError } from '../../../api/client'
import type { UserRole } from '../../../api/me'
import { useAccessToken } from '../../../auth/accessToken'
import { useCurrentUser } from '../../../auth/currentUser'
import { Button } from '../../../components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../../components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select'
import { formatDateTime } from '../../../lib/time'
import { USER_ROLES } from './adminUsersState'

type UserAction = { kind: 'approve' } | { kind: 'reject' } | { kind: 'change'; change: Omit<UserChange, 'version'> }

/** API'nin kullanıcı yönetimi hata kodları; her birinin kendi mesajı vardır (ekran akışları 5.2). */
const KNOWN_ERRORS = ['LAST_ACTIVE_ADMIN', 'VERSION_CONFLICT', 'INVALID_STATE_TRANSITION']

/** Liste kayıt bu arada değişti demektir: güncel hâli gösterilmeli. */
const STALE_ERRORS = ['VERSION_CONFLICT', 'INVALID_STATE_TRANSITION']

interface UserRowProps {
  user: AdminUser
  /** İşlemin sonucu: hata mesajı ya da başarılı işlemde `null` (önceki mesajı kaldırır). */
  onResult: (message: string | null) => void
}

/**
 * Kullanıcılar listesinde bir kullanıcı (ekran akışları 5.2). Onay bekleyen kullanıcıda Onayla ve
 * Reddet (onay penceresiyle); aktif ve pasif kullanıcıda rol ve durum seçimi; reddedilmiş kullanıcıda
 * işlem yoktur. İşlem sürerken satırın düğmeleri kapalıdır; sonuç listenin yeniden istenmesiyle görünür.
 */
export function UserRow({ user, onResult }: UserRowProps) {
  const { t } = useTranslation()
  const { locale } = useLocale()
  const accessToken = useAccessToken()
  const currentUser = useCurrentUser()
  const queryClient = useQueryClient()
  const [isRejectOpen, setRejectOpen] = useState(false)
  const name = user.displayName ?? user.email

  const action = useMutation({
    mutationFn: (action: UserAction) => {
      if (action.kind === 'approve') return approveUser(accessToken, user.id)
      if (action.kind === 'reject') return rejectUser(accessToken, user.id)
      return changeUser(accessToken, user.id, { ...action.change, version: user.version })
    },
    onSuccess: async (updated) => {
      onResult(null)
      // Yönetici kendi rolünü düşürdüyse menü ve bu sayfa güncel role göre yeniden çizilir.
      if (updated.id === currentUser.id) {
        await queryClient.invalidateQueries({ queryKey: ['me'] })
      }
      await queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
    onError: (error) => {
      const code = error instanceof ApiError ? error.code : undefined
      onResult(code && KNOWN_ERRORS.includes(code) ? t(`admin.users.errors.${code}`) : t('admin.users.errors.failed'))
      if (code && STALE_ERRORS.includes(code)) {
        void queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      }
    },
  })

  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-3 py-4">
      <div className="min-w-0 flex-1 basis-60">
        <p className="truncate font-medium">{name}</p>
        {user.displayName && <p className="truncate text-sm text-muted-foreground">{user.email}</p>}
        <p className="mt-1 text-xs text-muted-foreground">
          {t('admin.users.registeredAt', { date: formatDateTime(user.createdAt, locale) })}
        </p>
      </div>

      {user.status === 'PENDING' ? (
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">{t('userStatuses.PENDING')}</span>
          <Button size="sm" isDisabled={action.isPending} onPress={() => action.mutate({ kind: 'approve' })}>
            {t('admin.users.approve')}
          </Button>
          <Button size="sm" variant="outline" isDisabled={action.isPending} onPress={() => setRejectOpen(true)}>
            {t('admin.users.reject')}
          </Button>
          <Dialog isOpen={isRejectOpen} onOpenChange={setRejectOpen}>
            <DialogHeader>
              <DialogTitle>{t('admin.users.rejectDialog.title')}</DialogTitle>
              <DialogDescription>{t('admin.users.rejectDialog.text', { name })}</DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <DialogClose>{t('admin.users.rejectDialog.cancel')}</DialogClose>
              <Button
                variant="destructive"
                onPress={() => {
                  setRejectOpen(false)
                  action.mutate({ kind: 'reject' })
                }}
              >
                {t('admin.users.rejectDialog.confirm')}
              </Button>
            </DialogFooter>
          </Dialog>
        </div>
      ) : user.status === 'REJECTED' ? (
        <span className="text-sm text-muted-foreground">{t('userStatuses.REJECTED')}</span>
      ) : (
        <div className="flex items-center gap-2">
          <Select
            aria-label={t('admin.users.roleLabel', { name })}
            value={user.role}
            isDisabled={action.isPending}
            onChange={(key: Key | null) => {
              if (key && key !== user.role) action.mutate({ kind: 'change', change: { role: key as UserRole } })
            }}
          >
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {USER_ROLES.map((role) => (
                <SelectItem key={role} id={role}>
                  {t(`userRoles.${role}`)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            aria-label={t('admin.users.statusLabel', { name })}
            value={user.status}
            isDisabled={action.isPending}
            onChange={(key: Key | null) => {
              if (key && key !== user.status) {
                action.mutate({ kind: 'change', change: { status: key === 'PASSIVE' ? 'PASSIVE' : 'ACTIVE' } })
              }
            }}
          >
            <SelectTrigger className="w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem id="ACTIVE">{t('userStatuses.ACTIVE')}</SelectItem>
              <SelectItem id="PASSIVE">{t('userStatuses.PASSIVE')}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}
    </div>
  )
}
