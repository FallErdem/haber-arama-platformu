import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Checkbox, type Key } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { createFeed, updateFeed, type FeedChange, type ManagedFeed } from '../../../api/adminSources'
import { fetchCategories } from '../../../api/catalog'
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

/** Varsayılan kategorisi olmayan (karışık içerikli) besleme seçeneğinin kimliği; API'ye `null` gider. */
const NO_CATEGORY = 'NONE'

interface FeedDialogProps {
  sourceId: string
  /** Verilirse düzenleme, verilmezse ekleme penceresidir. */
  feed?: ManagedFeed
  isOpen: boolean
  onOpenChange: (isOpen: boolean) => void
  onSaved: () => Promise<unknown>
}

function initialForm(feed?: ManagedFeed) {
  return {
    name: feed?.name ?? '',
    url: feed?.url ?? '',
    defaultCategoryCode: feed?.defaultCategoryCode ?? NO_CATEGORY,
    useItemCategories: feed?.useItemCategories ?? true,
    fetchIntervalMinutes: String(feed?.fetchIntervalMinutes ?? 15),
  }
}

/**
 * Besleme ekleme ve düzenleme penceresi (FG-YP-04). Ekleme sonrası besleme hemen okunur (kaynak etkinse).
 * Düzenlemede yalnızca değişen alanlar, kaydın sürümüyle gönderilir. Besleme adresi değişirse API eski
 * adresin koşullu istek değerlerini siler.
 */
export function FeedDialog({ sourceId, feed, isOpen, onOpenChange, onSaved }: FeedDialogProps) {
  const { t } = useTranslation()
  const accessToken = useAccessToken()
  const [form, setForm] = useState(() => initialForm(feed))
  const categories = useQuery({
    queryKey: ['categories'],
    queryFn: () => fetchCategories(accessToken),
    enabled: isOpen,
  })

  const save = useMutation({
    mutationFn: () => {
      const settings = {
        name: form.name.trim(),
        url: form.url.trim(),
        defaultCategoryCode: form.defaultCategoryCode === NO_CATEGORY ? null : form.defaultCategoryCode,
        useItemCategories: form.useItemCategories,
        fetchIntervalMinutes: Number(form.fetchIntervalMinutes),
      }
      if (!feed) return createFeed(accessToken, sourceId, settings)
      const change: FeedChange = { version: feed.version }
      if (settings.name !== feed.name) change.name = settings.name
      if (settings.url !== feed.url) change.url = settings.url
      if (settings.defaultCategoryCode !== feed.defaultCategoryCode)
        change.defaultCategoryCode = settings.defaultCategoryCode
      if (settings.useItemCategories !== feed.useItemCategories) change.useItemCategories = settings.useItemCategories
      if (settings.fetchIntervalMinutes !== feed.fetchIntervalMinutes)
        change.fetchIntervalMinutes = settings.fetchIntervalMinutes
      return updateFeed(accessToken, feed.id, change)
    },
    onSuccess: async () => {
      await onSaved()
      onOpenChange(false)
      if (!feed) setForm(initialForm())
    },
  })
  const invalid = invalidFields(save.error)

  return (
    <Dialog isOpen={isOpen} onOpenChange={onOpenChange} className="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>{feed ? t('admin.feeds.editTitle') : t('admin.feeds.addTitle')}</DialogTitle>
        <DialogDescription>{t('admin.feeds.dialogText')}</DialogDescription>
      </DialogHeader>
      <form
        className="grid gap-3"
        onSubmit={(event) => {
          event.preventDefault()
          save.mutate()
        }}
      >
        <FormField
          label={t('admin.feeds.fields.name')}
          value={form.name}
          onChange={(name) => setForm({ ...form, name })}
          isInvalid={invalid.includes('name')}
          isRequired
        />
        <FormField
          label={t('admin.feeds.fields.url')}
          type="url"
          value={form.url}
          onChange={(url) => setForm({ ...form, url })}
          isInvalid={invalid.includes('url')}
          isRequired
        />
        <Select
          aria-label={t('admin.feeds.fields.defaultCategory')}
          value={form.defaultCategoryCode}
          onChange={(key: Key | null) => setForm({ ...form, defaultCategoryCode: String(key ?? NO_CATEGORY) })}
        >
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem id={NO_CATEGORY}>{t('admin.feeds.noCategory')}</SelectItem>
            {(categories.data ?? []).map((category) => (
              <SelectItem key={category.code} id={category.code}>
                {t(`categories.${category.code}`)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {/* React Aria Checkbox: klavyeyle (Boşluk) işaretlenir, durumunu ekran okuyucuya bildirir. */}
        <Checkbox
          isSelected={form.useItemCategories}
          onChange={(useItemCategories) => setForm({ ...form, useItemCategories })}
          className="group flex items-center gap-2 text-sm"
        >
          <span
            aria-hidden
            className="flex size-4 items-center justify-center rounded border border-input group-data-focus-visible:ring-3 group-data-focus-visible:ring-ring/50 group-data-selected:border-primary group-data-selected:bg-primary group-data-selected:text-primary-foreground"
          >
            <svg viewBox="0 0 16 16" className="hidden size-3 group-data-selected:block" fill="none">
              <path d="M3 8l3 3 7-7" stroke="currentColor" strokeWidth="2" />
            </svg>
          </span>
          {t('admin.feeds.fields.useItemCategories')}
        </Checkbox>
        <FormField
          label={t('admin.feeds.fields.fetchIntervalMinutes')}
          type="number"
          value={form.fetchIntervalMinutes}
          onChange={(fetchIntervalMinutes) => setForm({ ...form, fetchIntervalMinutes })}
          isInvalid={invalid.includes('fetchIntervalMinutes')}
          isRequired
        />
        {save.isError && (
          <p role="alert" className="text-sm text-destructive">
            {adminErrorMessage(save.error, t)}
          </p>
        )}
        <DialogFooter>
          <DialogClose>{t('admin.cancel')}</DialogClose>
          <Button type="submit" isDisabled={save.isPending}>
            {t('admin.save')}
          </Button>
        </DialogFooter>
      </form>
    </Dialog>
  )
}
