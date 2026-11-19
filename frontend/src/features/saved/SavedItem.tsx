import { useLocale } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { Link, useLocation } from 'react-router'
import type { SavedArticleItem } from '../../api/savedArticles'
import { formatPublishedAt } from '../../lib/time'
import { Thumbnail } from '../search/ResultItem'
import { BookmarkToggle } from './BookmarkToggle'
import { useSaveArticle } from './useSaveArticle'

/**
 * Kaydedilenler listesindeki bir haber: görsel, kaynak ve yayın zamanı, başlık ve sağ üstte dolu yer
 * imi; yer imine basmak haberi kayıttan çıkarır. Haber sonradan gizlendiyse yalnızca bunu söyleyen
 * bir satır gösterilir; detayına geçilemez, yalnızca kayıttan çıkarılabilir (FG-KO-03).
 */
export function SavedItem({ item }: { item: SavedArticleItem }) {
  const { t } = useTranslation()
  const { locale } = useLocale()
  const location = useLocation()
  const bookmark = useSaveArticle(item.articleId, true)
  const { article } = item

  return (
    <article className="flex gap-4 py-5 sm:gap-5">
      <Thumbnail image={article?.image ?? null} />
      <div className="min-w-0 flex-1">
        {article ? (
          <>
            <p className="text-xs text-muted-foreground">
              <span className="font-medium tracking-wide uppercase">{article.source.name}</span>
              <span aria-hidden> · </span>
              <time dateTime={article.publishedAt}>{formatPublishedAt(article.publishedAt, locale)}</time>
            </p>
            <h2 className="mt-1 text-lg leading-snug font-semibold sm:text-xl">
              {/* state: detaydaki geri bağlantısı Kaydedilenlerin bu sayfasına döner. */}
              <Link
                to={`/articles/${item.articleId}`}
                state={{ from: 'saved', search: location.search }}
                className="decoration-1 underline-offset-4 hover:underline"
              >
                {article.title}
              </Link>
            </h2>
          </>
        ) : (
          <p className="text-sm text-muted-foreground italic">{t('saved.hidden')}</p>
        )}
        {bookmark.isError && (
          <p role="alert" className="mt-2 text-xs text-destructive">
            {t('bookmark.failed')}
          </p>
        )}
      </div>
      <BookmarkToggle
        isSaved={bookmark.isSaved}
        onChange={bookmark.setSaved}
        isDisabled={bookmark.isPending}
        title={article?.title ?? t('saved.hidden')}
        className="-mt-1.5 -mr-2"
      />
    </article>
  )
}
