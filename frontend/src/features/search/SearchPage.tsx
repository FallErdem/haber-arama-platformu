import { useTranslation } from 'react-i18next'

/** Arama ekranı (ana sayfa). Arama kutusu, filtreler ve sonuçlar 3. parçada eklenecek. */
export function SearchPage() {
  const { t } = useTranslation()

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <h1 className="text-3xl font-semibold tracking-tight">{t('search.title')}</h1>
    </div>
  )
}
