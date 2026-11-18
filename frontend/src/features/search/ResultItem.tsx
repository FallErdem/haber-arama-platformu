import { NewspaperIcon } from 'lucide-react'
import { useLocale } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { Link, useLocation } from 'react-router'
import type { ArticleImage, ArticleSearchItem } from '../../api/articles'
import { formatPublishedAt } from '../../lib/time'
import { Highlighted } from './Highlighted'

/**
 * Arama sonucundaki bir haber: görsel, kaynak ve yayın zamanı, başlık, iki satır özet (ekran akışları
 * 5.1). Arama ifadesi varsa başlık ve özetteki eşleşmeler vurgulanır (FG-AR-05).
 */
export function ResultItem({ item }: { item: ArticleSearchItem }) {
  const { t } = useTranslation()
  const { locale } = useLocale()
  const location = useLocation()
  const title = item.highlights?.title?.[0]
  const summary = item.highlights?.summary?.[0]

  return (
    // lang: İngilizce haberi ekran okuyucu İngilizce telaffuzla okur (WCAG 3.1.2).
    <article lang={item.language} className="flex gap-4 py-5 sm:gap-5">
      <Thumbnail image={item.image} />
      <div className="min-w-0 flex-1">
        <p className="text-xs text-muted-foreground">
          <span className="font-medium tracking-wide uppercase">{item.source.name}</span>
          <span aria-hidden> · </span>
          <time dateTime={item.publishedAt}>{formatPublishedAt(item.publishedAt, locale)}</time>
        </p>
        <h2 className="mt-1 text-lg leading-snug font-semibold sm:text-xl">
          {/* state: detay sayfasındaki "Aramaya dön" bu aramaya (filtreler ve sayfa dahil) döner. */}
          <Link
            to={`/articles/${item.id}`}
            state={{ search: location.search }}
            className="decoration-1 underline-offset-4 hover:underline"
          >
            {title ? <Highlighted fragment={title} /> : item.title}
          </Link>
        </h2>
        {(summary ?? item.summary) && (
          <p className="mt-1.5 line-clamp-2 text-sm leading-relaxed text-muted-foreground">
            {summary ? <Highlighted fragment={summary} /> : item.summary}
          </p>
        )}
        {item.otherSourcesCount > 0 && (
          <p className="mt-2 text-xs text-muted-foreground">
            {t('search.moreSources', { count: item.otherSourcesCount })}
          </p>
        )}
      </div>
    </article>
  )
}

/**
 * Haberin ana görseli; yoksa yer tutucu (FG-AR-08). Görsel başlığın hemen yanında olduğu için
 * alternatif metni boştur: ekran okuyucu başlığı iki kez okumaz.
 */
function Thumbnail({ image }: { image: ArticleImage | null }) {
  const className = 'aspect-[4/3] w-24 shrink-0 rounded-sm bg-muted sm:w-36'
  if (!image) {
    return (
      <div aria-hidden className={`${className} flex items-center justify-center text-muted-foreground`}>
        <NewspaperIcon className="size-6 opacity-40" />
      </div>
    )
  }
  return (
    <img
      src={image.url}
      alt=""
      width={image.width}
      height={image.height}
      // Görünür alana gelmeyen görseller indirilmez; sayfa daha hızlı açılır.
      loading="lazy"
      decoding="async"
      className={`${className} object-cover`}
    />
  )
}
