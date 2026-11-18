import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

/** Tanımlı olmayan bir adres veya bulunamayan bir kayıt için gösterilir (ekran akışları 5.1). */
export function NotFoundPage() {
  const { t } = useTranslation()

  return (
    <div className="mx-auto max-w-2xl px-4 py-20 text-center sm:px-6">
      <h1 className="text-3xl font-semibold tracking-tight">{t('notFound.title')}</h1>
      <p className="mt-3 text-muted-foreground">{t('notFound.text')}</p>
      <Link to="/" className="mt-8 inline-block text-primary underline-offset-4 hover:underline">
        {t('notFound.back')}
      </Link>
    </div>
  )
}
