import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import type { Key } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'
import { createSource, type NewSource } from '../../../api/adminSources'
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select'
import { adminErrorMessage, invalidFields } from '../adminErrors'
import { FormField } from '../FormField'

interface CreateSourceDialogProps {
  isOpen: boolean
  onOpenChange: (isOpen: boolean) => void
}

const EMPTY = { code: '', name: '', homepageUrl: '', requestIntervalSeconds: '5' }

/**
 * Kaynak ekleme penceresi (ekran akışları 4.3). Kaynak devre dışı eklenir; eklenince kaynağın detayına
 * geçilir, orada beslemeleri eklenip kaynak etkinleştirilir. Kod, okuyucu türü ve dil sonradan
 * değiştirilemez (sözleşme 6.2); pencere bunu söyler.
 */
export function CreateSourceDialog({ isOpen, onOpenChange }: CreateSourceDialogProps) {
  const { t } = useTranslation()
  const accessToken = useAccessToken()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [form, setForm] = useState(EMPTY)
  const [readerType, setReaderType] = useState<NewSource['readerType']>('RSS')
  const [language, setLanguage] = useState<NewSource['language']>('tr')

  const create = useMutation({
    mutationFn: () =>
      createSource(accessToken, {
        code: form.code.trim(),
        name: form.name.trim(),
        homepageUrl: form.homepageUrl.trim(),
        readerType,
        language,
        requestIntervalSeconds: Number(form.requestIntervalSeconds),
      }),
    onSuccess: async (source) => {
      await queryClient.invalidateQueries({ queryKey: ['admin-sources'] })
      onOpenChange(false)
      setForm(EMPTY)
      void navigate(`/admin/sources/${source.id}`)
    },
  })
  const invalid = invalidFields(create.error)
  const set = (field: keyof typeof EMPTY) => (value: string) => setForm({ ...form, [field]: value })

  return (
    <Dialog isOpen={isOpen} onOpenChange={onOpenChange} className="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>{t('admin.sources.createTitle')}</DialogTitle>
        <DialogDescription>{t('admin.sources.createText')}</DialogDescription>
      </DialogHeader>
      <form
        className="grid gap-3"
        onSubmit={(event) => {
          event.preventDefault()
          create.mutate()
        }}
      >
        <FormField
          label={t('admin.sources.fields.code')}
          description={t('admin.sources.fields.codeHint')}
          value={form.code}
          onChange={set('code')}
          isInvalid={invalid.includes('code')}
          isRequired
        />
        <FormField
          label={t('admin.sources.fields.name')}
          value={form.name}
          onChange={set('name')}
          isInvalid={invalid.includes('name')}
          isRequired
        />
        <FormField
          label={t('admin.sources.fields.homepageUrl')}
          type="url"
          value={form.homepageUrl}
          onChange={set('homepageUrl')}
          isInvalid={invalid.includes('homepageUrl')}
          isRequired
        />
        <div className="grid grid-cols-2 gap-3">
          <Select
            aria-label={t('admin.sources.fields.readerType')}
            value={readerType}
            onChange={(key: Key | null) => setReaderType(key === 'ATOM' ? 'ATOM' : 'RSS')}
          >
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem id="RSS">RSS</SelectItem>
              <SelectItem id="ATOM">Atom</SelectItem>
            </SelectContent>
          </Select>
          <Select
            aria-label={t('admin.sources.fields.language')}
            value={language}
            onChange={(key: Key | null) => setLanguage(key === 'en' ? 'en' : 'tr')}
          >
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem id="tr">{t('languages.tr')}</SelectItem>
              <SelectItem id="en">{t('languages.en')}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <FormField
          label={t('admin.sources.fields.requestIntervalSeconds')}
          description={t('admin.sources.fields.requestIntervalHint')}
          type="number"
          value={form.requestIntervalSeconds}
          onChange={set('requestIntervalSeconds')}
          isInvalid={invalid.includes('requestIntervalSeconds')}
          isRequired
        />
        {create.isError && (
          <p role="alert" className="text-sm text-destructive">
            {adminErrorMessage(create.error, t)}
          </p>
        )}
        <DialogFooter>
          <DialogClose>{t('admin.cancel')}</DialogClose>
          <Button type="submit" isDisabled={create.isPending}>
            {t('admin.sources.create')}
          </Button>
        </DialogFooter>
      </form>
    </Dialog>
  )
}
