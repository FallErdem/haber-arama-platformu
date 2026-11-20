import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { updateSource, type ManagedSource, type SourceChange } from '../../../api/adminSources'
import { useAccessToken } from '../../../auth/accessToken'
import { Button } from '../../../components/ui/button'
import { invalidFields } from '../adminErrors'
import { FormField } from '../FormField'

interface SourceSettingsFormProps {
  source: ManagedSource
  onSaved: () => Promise<unknown>
  onError: (error: Error) => void
}

/** Formdaki değerler metin olarak tutulur; boş alan, boş bırakılabilen ayarda "yok" demektir. */
function initialForm(source: ManagedSource) {
  return {
    name: source.name,
    homepageUrl: source.homepageUrl,
    requestIntervalSeconds: String(source.requestIntervalSeconds),
    dailyRequestLimit: source.dailyRequestLimit === null ? '' : String(source.dailyRequestLimit),
    license: source.license ?? '',
    attributionText: source.attributionText ?? '',
    feedTimeZone: source.feedTimeZone ?? '',
  }
}

type Form = ReturnType<typeof initialForm>

/**
 * Yalnızca değişen alanları gönderir (sözleşme 2.5). Boşaltılan bir ayar (örneğin lisans) `null` olarak
 * gönderilir; API alanı boşaltır.
 */
function toChange(source: ManagedSource, form: Form): SourceChange {
  const before = initialForm(source)
  const change: SourceChange = { version: source.version }
  const changed = (field: keyof Form) => form[field].trim() !== before[field]
  if (changed('name')) change.name = form.name.trim()
  if (changed('homepageUrl')) change.homepageUrl = form.homepageUrl.trim()
  if (changed('requestIntervalSeconds')) change.requestIntervalSeconds = Number(form.requestIntervalSeconds)
  if (changed('dailyRequestLimit')) {
    change.dailyRequestLimit = form.dailyRequestLimit.trim() === '' ? null : Number(form.dailyRequestLimit)
  }
  if (changed('license')) change.license = form.license.trim() || null
  if (changed('attributionText')) change.attributionText = form.attributionText.trim() || null
  if (changed('feedTimeZone')) change.feedTimeZone = form.feedTimeZone.trim() || null
  return change
}

/** Kaynağın ayarları. Kod, okuyucu türü ve dil burada yoktur: sonradan değiştirilemezler (sözleşme 6.2). */
export function SourceSettingsForm({ source, onSaved, onError }: SourceSettingsFormProps) {
  const { t } = useTranslation()
  const accessToken = useAccessToken()
  const [form, setForm] = useState(() => initialForm(source))
  const save = useMutation({
    mutationFn: () => updateSource(accessToken, source.id, toChange(source, form)),
    onSuccess: onSaved,
    onError,
  })
  const invalid = invalidFields(save.error)
  const field = (name: keyof Form) => ({
    value: form[name],
    onChange: (value: string) => setForm({ ...form, [name]: value }),
    isInvalid: invalid.includes(name),
  })

  return (
    <form
      className="mt-4 grid max-w-xl gap-3"
      onSubmit={(event) => {
        event.preventDefault()
        save.mutate()
      }}
    >
      <FormField label={t('admin.sources.fields.name')} isRequired {...field('name')} />
      <FormField label={t('admin.sources.fields.homepageUrl')} type="url" isRequired {...field('homepageUrl')} />
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField
          label={t('admin.sources.fields.requestIntervalSeconds')}
          description={t('admin.sources.fields.requestIntervalHint')}
          type="number"
          isRequired
          {...field('requestIntervalSeconds')}
        />
        <FormField
          label={t('admin.sources.fields.dailyRequestLimit')}
          description={t('admin.sources.fields.dailyRequestLimitHint')}
          type="number"
          {...field('dailyRequestLimit')}
        />
      </div>
      <FormField label={t('admin.sources.fields.license')} {...field('license')} />
      <FormField label={t('admin.sources.fields.attributionText')} {...field('attributionText')} />
      <FormField
        label={t('admin.sources.fields.feedTimeZone')}
        description={t('admin.sources.fields.feedTimeZoneHint')}
        {...field('feedTimeZone')}
      />
      <div>
        <Button type="submit" isDisabled={save.isPending}>
          {t('admin.save')}
        </Button>
      </div>
    </form>
  )
}
