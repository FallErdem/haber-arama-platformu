import { useQuery } from '@tanstack/react-query'
import { ArrowLeftIcon, EyeOffIcon } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useLocale } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { Link, useLocation, useParams } from 'react-router'
import { fetchArticle, type ArticleDetail } from '../../api/articles'
import { ApiError } from '../../api/client'
import { useAccessToken } from '../../auth/accessToken'
import { useCurrentUser } from '../../auth/currentUser'
import { Button } from '../../components/ui/button'
import { formatDateTime } from '../../lib/time'
import { NotFoundPage } from '../errors/NotFoundPage'
import { BookmarkToggle } from '../saved/BookmarkToggle'
import { useSaveArticle } from '../saved/useSaveArticle'
import { HideArticleDialog } from './HideArticleDialog'
import { sanitizeContent } from './sanitize'
import { SourceAttribution } from './SourceAttribution'

/** Haber kimlikleri UUID'dir; başka bir değerle API'ye boşuna istek gönderilmez. */
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

/**
 * Detaya gelinen sayfa: arama veya Kaydedilenler kendi adres parametrelerini (`?q=...`, `?page=2`)
 * buraya bırakır; geri bağlantısı aynı sayfaya, aynı filtrelerle döner.
 */
interface CameFrom {
  from?: 'saved'
  search?: string
}

/**
 * Haber detayı (ekran akışları 5.1; FG-AR-06, FG-AR-07). Meta veri ve görseller PostgreSQL'den, özet,
 * tam metin ve yazar Elasticsearch'ten gelir; API ikisini birleştirip tek yanıtta döner (ADR-0019).
 *
 * Yönetici haberi buradan gizleyebilir (FG-YP-09). Gizlenen haber kimseye gösterilmediği için haberin yerine
 * "Haber gizlendi" mesajı çıkar; yönetici aramaya dönebilir veya gizlemeyi Gizlenen haberler ekranından geri
 * alabilir.
 */
export function ArticlePage() {
  const { articleId = '' } = useParams()
  const isValidId = UUID.test(articleId)
  const accessToken = useAccessToken()
  const { t } = useTranslation()
  const location = useLocation()
  const cameFrom = location.state as CameFrom | null
  const fromSaved = cameFrom?.from === 'saved'
  const backTo = `${fromSaved ? '/saved' : '/'}${cameFrom?.search ?? ''}`
  const [isHidden, setHidden] = useState(false)

  const article = useQuery({
    queryKey: ['article', articleId],
    queryFn: () => fetchArticle(accessToken, articleId),
    enabled: isValidId,
  })

  // Az önce gizlenen haber yeniden istenirse 404 döner; bulunamadı sayfası yerine gizlendi mesajı kalır.
  if (!isValidId || (!isHidden && article.error instanceof ApiError && article.error.status === 404)) {
    return <NotFoundPage />
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6 sm:py-10">
      <Link
        to={backTo}
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeftIcon aria-hidden className="size-4" />
        {fromSaved ? t('article.backToSaved') : t('article.back')}
      </Link>

      {isHidden ? (
        <HiddenNotice backTo={backTo} fromSaved={fromSaved} />
      ) : article.isPending ? (
        <p className="mt-10 text-muted-foreground">{t('article.loading')}</p>
      ) : article.isError ? (
        <div role="alert" className="mt-10">
          <p>
            {article.error instanceof ApiError && article.error.code === 'SEARCH_UNAVAILABLE'
              ? t('article.textUnavailable')
              : t('article.loadFailed')}
          </p>
          <Button variant="outline" className="mt-4" onPress={() => void article.refetch()}>
            {t('article.retry')}
          </Button>
        </div>
      ) : (
        <ArticleView article={article.data} onHidden={() => setHidden(true)} />
      )}
    </div>
  )
}

/** Gizlemeden sonra haberin yerine gösterilen mesaj. */
function HiddenNotice({ backTo, fromSaved }: { backTo: string; fromSaved: boolean }) {
  const { t } = useTranslation()
  const linkClass = 'text-sm font-medium text-primary underline-offset-4 hover:underline'
  return (
    <div role="status" className="mt-10 rounded-lg border border-border bg-card p-6">
      <h1 className="text-2xl font-semibold tracking-tight">{t('article.hidden.title')}</h1>
      <p className="mt-2 text-muted-foreground">{t('article.hidden.text')}</p>
      <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2">
        <Link to={backTo} className={linkClass}>
          {fromSaved ? t('article.backToSaved') : t('article.back')}
        </Link>
        <Link to="/admin/hidden-articles" className={linkClass}>
          {t('article.hidden.list')}
        </Link>
      </div>
    </div>
  )
}

function ArticleView({ article, onHidden }: { article: ArticleDetail; onHidden: () => void }) {
  const { t } = useTranslation()
  const { locale } = useLocale()
  const currentUser = useCurrentUser()
  const [isHideOpen, setHideOpen] = useState(false)
  const content = useMemo(() => (article.content ? sanitizeContent(article.content) : null), [article.content])
  const bookmark = useSaveArticle(article.id, article.saved)
  const [mainImage, ...otherImages] = article.media

  // Sekmede haberin başlığı görünür; sayfadan çıkınca uygulamanın adına döner.
  useEffect(() => {
    document.title = `${article.title} · ${t('app.title')}`
    return () => {
      document.title = t('app.title')
    }
  }, [article.title, t])

  return (
    // lang: İngilizce haberi ekran okuyucu İngilizce telaffuzla okur (WCAG 3.1.2).
    <article lang={article.language} className="mt-6">
      <header>
        <div className="flex items-center justify-between gap-4">
          <p className="text-xs text-muted-foreground">
            <span className="font-medium tracking-wide uppercase">{article.source.name}</span>
            <span aria-hidden> · </span>
            <time dateTime={article.publishedAt}>{formatDateTime(article.publishedAt, locale)}</time>
          </p>
          <div className="flex items-center gap-1">
            {/* Yalnızca yöneticiye görünür; bu bir kolaylıktır, yetki kontrolü backend'dedir. */}
            {currentUser.role === 'ADMIN' && (
              <Button variant="ghost" size="sm" onPress={() => setHideOpen(true)}>
                <EyeOffIcon aria-hidden />
                {t('article.hide.button')}
              </Button>
            )}
            <BookmarkToggle
              isSaved={bookmark.isSaved}
              onChange={bookmark.setSaved}
              isDisabled={bookmark.isPending}
              className="-mr-2"
            />
          </div>
        </div>
        {currentUser.role === 'ADMIN' && (
          <HideArticleDialog
            articleId={article.id}
            isOpen={isHideOpen}
            onOpenChange={setHideOpen}
            onHidden={onHidden}
          />
        )}
        {bookmark.isError && (
          <p role="alert" className="mt-1 text-right text-xs text-destructive">
            {t('bookmark.failed')}
          </p>
        )}
        <h1 className="mt-2 text-3xl leading-tight font-semibold tracking-tight sm:text-4xl">{article.title}</h1>
        {article.author && (
          <p className="mt-3 text-sm text-muted-foreground">{t('article.byAuthor', { author: article.author })}</p>
        )}
        {article.categories.length > 0 && (
          <ul aria-label={t('article.categories')} className="mt-4 flex flex-wrap gap-1.5">
            {article.categories.map((code) => (
              <li key={code} className="rounded-full border border-border px-2.5 py-0.5 text-xs text-muted-foreground">
                {t(`categories.${code}`)}
              </li>
            ))}
          </ul>
        )}
      </header>

      {mainImage && <ArticleFigure media={mainImage} title={article.title} className="mt-6" />}

      <div className="mt-6">
        {content ? (
          // Temizlenmiş HTML (sanitize.ts); işçi de kaydederken temizledi (FOG-16).
          <div className="article-body" dangerouslySetInnerHTML={{ __html: content }} />
        ) : article.summary ? (
          // Kaynak tam metin vermiyorsa özet gösterilir (FG-AR-06).
          <p className="article-body">{article.summary}</p>
        ) : (
          // Haber yeni kaydedildi, metni arama indeksine birkaç saniye içinde aktarılacak (ADR-0019).
          <p className="text-muted-foreground">{t('article.textPending')}</p>
        )}
      </div>

      {otherImages.map((media) => (
        <ArticleFigure key={media.url} media={media} title={article.title} className="mt-6" />
      ))}

      {article.otherSources.length > 0 && (
        <section className="mt-10">
          <h2 className="text-lg font-semibold">{t('article.otherSources')}</h2>
          <ul className="mt-3 space-y-1.5 text-sm">
            {article.otherSources.map((other) => (
              <li key={other.articleId}>
                <a href={other.url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                  {other.source.name}
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}

      <SourceAttribution article={article} />
    </article>
  )
}

/**
 * Haberin görseli; altyazısı ve fotoğrafçı bilgisiyle. Alternatif metin görselin altyazısı, yoksa
 * haberin başlığıdır (ekran akışları 2. bölüm). Genişlik ve yükseklik verildiği için görsel yüklenirken
 * sayfa kaymaz.
 */
function ArticleFigure({
  media,
  title,
  className,
}: {
  media: ArticleDetail['media'][number]
  title: string
  className?: string
}) {
  const { t } = useTranslation()

  return (
    <figure className={className}>
      <img
        src={media.url}
        alt={media.caption ?? title}
        width={media.width}
        height={media.height}
        className="h-auto w-full rounded-sm bg-muted"
      />
      {(media.caption || media.credit) && (
        <figcaption className="mt-2 text-xs text-muted-foreground">
          {media.caption}
          {media.caption && media.credit && ' · '}
          {media.credit && t('article.photoCredit', { credit: media.credit })}
        </figcaption>
      )}
    </figure>
  )
}
