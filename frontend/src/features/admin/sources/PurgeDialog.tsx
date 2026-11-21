import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { requestPurge, type ManagedSource } from '../../../api/adminSources'
import { useAccessToken } from '../../../auth/accessToken'
import { Button } from '../../../components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../../components/ui/dialog'
import { adminErrorMessage, invalidFields, isStaleError } from '../adminErrors'
import { FormField } from '../FormField'

interface PurgeDialogProps {
  source: ManagedSource
  isOpen: boolean
  onOpenChange: (isOpen: boolean) => void
  /** Silme istendi: ekran sonucu duyurur. */
  onRequested: () => void
  /** Kaynağın detayını yeniden ister. */
  refresh: () => Promise<unknown>
}

/**
 * Kaynak içeriğini silme penceresi (ekran akışları 4.5; FG-YP-14). Silme geri alınamaz: pencere kaç haberin
 * silineceğini söyler ve kaynağın kodunun yazılmasını ister; kod doğru yazılmadan onay düğmesi çalışmaz.
 * API de aynı kodu ister (sözleşme 6.2).
 */
export function PurgeDialog({ source, isOpen, onOpenChange, onRequested, refresh }: PurgeDialogProps) {
  const { t } = useTranslation()
  const accessToken = useAccessToken()
  const [code, setCode] = useState('')

  const purge = useMutation({
    mutationFn: () => requestPurge(accessToken, source.id, code.trim()),
    onSuccess: async () => {
      close()
      onRequested()
      await refresh()
    },
    // Kaynak bu arada değiştiyse (etkinleştirildi, silme başladı) ekran güncellenir.
    onError: (error) => {
      if (isStaleError(error)) void refresh()
    },
  })

  /** Pencere kapanınca yazılan kod ve eski hata unutulur. */
  function close() {
    setCode('')
    purge.reset()
    onOpenChange(false)
  }

  return (
    <Dialog isOpen={isOpen} onOpenChange={(open) => (open ? onOpenChange(true) : close())} className="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>{t('admin.sources.purgeTitle')}</DialogTitle>
        <DialogDescription>
          {t('admin.sources.purgeText', { name: source.name, count: source.articleCount })}
        </DialogDescription>
      </DialogHeader>
      <form
        className="grid gap-3"
        onSubmit={(event) => {
          event.preventDefault()
          purge.mutate()
        }}
      >
        <FormField
          label={t('admin.sources.purgeConfirmLabel', { code: source.code })}
          value={code}
          onChange={setCode}
          isInvalid={invalidFields(purge.error).includes('confirmationCode')}
          isRequired
        />
        {purge.isError && (
          <p role="alert" className="text-sm text-destructive">
            {adminErrorMessage(purge.error, t)}
          </p>
        )}
        <DialogFooter>
          <DialogClose>{t('admin.cancel')}</DialogClose>
          <Button type="submit" variant="destructive" isDisabled={code.trim() !== source.code || purge.isPending}>
            {t('admin.sources.purgeConfirm')}
          </Button>
        </DialogFooter>
      </form>
    </Dialog>
  )
}
