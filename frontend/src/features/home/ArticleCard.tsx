import { NewspaperIcon } from 'lucide-react'
import { useLocale } from 'react-aria-components'
import { Link } from 'react-router'
import type { ArticleSearchItem } from '../../api/articles'
import { formatPublishedAt } from '../../lib/time'
import { BreakingBadge, SourceBadge } from '../search/ArticleBadges'

/**
 * Dikey haber kartı: görsel üstte, altında kaynak, zaman ve başlık. Ana sayfanın kategori bölümleri ve haber
 * detayındaki ilgili haberler kullanır. Görselin alternatif metni boştur; başlık hemen altında okunur.
 */
export function ArticleCard({ item }: { item: ArticleSearchItem }) {
  const { locale } = useLocale()

  return (
    // lang: İngilizce haberi ekran okuyucu İngilizce telaffuzla okur (WCAG 3.1.2).
    <article lang={item.language} className="flex flex-col">
      {item.image ? (
        <img
          src={item.image.url}
          alt=""
          width={item.image.width}
          height={item.image.height}
          loading="lazy"
          decoding="async"
          className="aspect-[16/10] w-full rounded-sm bg-muted object-cover"
        />
      ) : (
        <div
          aria-hidden
          className="flex aspect-[16/10] w-full items-center justify-center rounded-sm bg-muted text-muted-foreground"
        >
          <NewspaperIcon className="size-7 opacity-40" />
        </div>
      )}
      <p className="mt-2.5 flex items-center gap-1.5 text-xs text-muted-foreground">
        <SourceBadge source={item.source} />
        <span className="truncate font-medium tracking-wide uppercase">{item.source.name}</span>
        <span aria-hidden>·</span>
        <time dateTime={item.publishedAt} className="shrink-0">
          {formatPublishedAt(item.publishedAt, locale)}
        </time>
      </p>
      <BreakingBadge categories={item.categories} className="mt-2 self-start" />
      <h3 className="mt-1.5 line-clamp-3 font-heading text-base leading-snug font-semibold">
        <Link to={`/articles/${item.id}`} className="decoration-1 underline-offset-4 hover:underline">
          {item.title}
        </Link>
      </h3>
    </article>
  )
}
