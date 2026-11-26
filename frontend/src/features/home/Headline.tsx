import { useQuery } from '@tanstack/react-query'
import { cn } from 'cn'
import { ChevronLeftIcon, ChevronRightIcon, PauseIcon, PlayIcon } from 'lucide-react'
import { useState } from 'react'
import { useLocale } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { type ArticleSearchItem, searchArticles } from '../../api/articles'
import { useAccessToken } from '../../auth/accessToken'
import { Button } from '../../components/ui/button'
import { formatPublishedAt } from '../../lib/time'
import { BreakingBadge } from '../search/ArticleBadges'
import { BREAKING } from '../search/useCategories'
import { HOME_QUERY_KEY } from './queryKeys'

/** Manşetteki haber sayısı: yandaki liste görselin boyunu dolduracak kadar. */
const SLIDE_COUNT = 8
/** Görselli haberleri seçmek için istenen aday sayısı; görselsiz haberler elenir. */
const CANDIDATES = 30
/** Görselli son dakika yetmezse manşet bu kategoriden tamamlanır. */
const FALLBACK_CATEGORY = 'GENERAL'
/** Manşet bu aralıkla sonraki habere geçer: görselin altındaki çubuk bu sürede dolar. */
const INTERVAL_MS = 10_000

/**
 * Manşetin haberleri: görselli en yeni son dakika haberleri; yetmezse Gündem'in görselli haberleriyle
 * tamamlanır. Manşette büyük görsel gösterildiği için görselsiz haber alınmaz.
 */
async function fetchHeadlines(accessToken: string): Promise<ArticleSearchItem[]> {
  const withImage = async (category: string) =>
    (
      await searchArticles(accessToken, new URLSearchParams({ categories: category, size: String(CANDIDATES) }))
    ).items.filter((item) => item.image !== null)
  const breaking = await withImage(BREAKING)
  if (breaking.length >= SLIDE_COUNT) {
    return breaking.slice(0, SLIDE_COUNT)
  }
  const general = (await withImage(FALLBACK_CATEGORY)).filter((item) => !breaking.some((b) => b.id === item.id))
  return [...breaking, ...general].slice(0, SLIDE_COUNT)
}

/**
 * Ana sayfanın en üstündeki manşet (gazetenin birinci sayfası gibi). Haberler bölümler gibi bir kez istenir ve
 * Yenile düğmesiyle güncellenir (aynı anahtar ailesi); gösterilen haber ise 15 saniyede bir yana kayarak değişir.
 * Görselli haber yoksa manşet hiç gösterilmez.
 */
export function Headline() {
  const accessToken = useAccessToken()
  const headlines = useQuery({
    queryKey: [HOME_QUERY_KEY, 'headline'],
    queryFn: () => fetchHeadlines(accessToken),
    staleTime: Infinity,
  })

  if (headlines.isPending) {
    return (
      <div
        aria-hidden
        className="aspect-[16/9] animate-pulse rounded-md bg-muted motion-reduce:animate-none lg:w-2/3"
      />
    )
  }
  if (!headlines.isSuccess || headlines.data.length === 0) {
    return null
  }
  // key: Yenile'den sonra yeni haberlerle döngü baştan başlar.
  return <HeadlineCarousel key={headlines.data.map((item) => item.id).join()} slides={headlines.data} />
}

/**
 * Döngülü manşet (WAI-ARIA APG, Carousel kalıbı). Görselin altındaki çubuk 10 saniyede dolar; dolunca sonraki habere
 * geçilir. Geçişi ayrı bir zamanlayıcı değil çubuğun animasyonunun bitişi yapar: çubuk ile geçiş hiç kaymaz.
 *
 * Kendiliğinden değişen içerik durdurulabilmelidir (WCAG 2.2.2): "Durdur" düğmesi döngüyü kapatır. Fare görselin
 * üzerindeyken (klavyede: görseldeki bağlantıya odaklanınca) çubuk olduğu yerde bekler, sonra kaldığı yerden devam
 * eder. Elle geçince çubuk baştan başlar. Döngü sürerken değişiklik ekran okuyucuya duyurulmaz (aria-live="off").
 * Hareketi azaltma ayarı açıksa haberler kaymadan, yerinde değişir.
 */
function HeadlineCarousel({ slides }: { slides: ArticleSearchItem[] }) {
  const { t } = useTranslation()
  const { locale } = useLocale()
  const [index, setIndex] = useState(0)
  const [isPaused, setPaused] = useState(false)
  const [isHovered, setHovered] = useState(false)
  const [hasFocus, setFocus] = useState(false)
  const canRotate = slides.length > 1
  const isRotating = canRotate && !isPaused && !isHovered && !hasFocus

  const show = (next: number) => setIndex((next + slides.length) % slides.length)

  return (
    <section
      aria-roledescription={t('home.headline.carousel')}
      aria-label={t('home.headline.label')}
      className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)] lg:gap-8"
    >
      <div className="min-w-0">
        {/* Duraklatma yalnızca görselin üzerinde: düğmelere veya yandaki listeye gelmek döngüyü durdurmaz. */}
        <div
          className="overflow-hidden rounded-md"
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
          onFocus={() => setFocus(true)}
          onBlur={(event) => {
            if (!event.currentTarget.contains(event.relatedTarget)) setFocus(false)
          }}
        >
          <div
            aria-live={isRotating ? 'off' : 'polite'}
            className="flex transition-transform duration-700 ease-in-out motion-reduce:transition-none"
            style={{ transform: `translateX(-${index * 100}%)` }}
          >
            {slides.map((item, position) => (
              <Slide
                key={item.id}
                item={item}
                position={position}
                count={slides.length}
                isActive={position === index}
              />
            ))}
          </div>
          {canRotate && (
            <div aria-hidden className="h-1 bg-muted">
              {/* key: haber değişince (kendiliğinden veya elle) çubuk baştan dolmaya başlar. */}
              <div
                key={index}
                data-slot="headline-progress"
                className="h-full origin-left bg-primary"
                style={{
                  animation: `headline-progress ${INTERVAL_MS}ms linear forwards`,
                  animationPlayState: isRotating ? 'running' : 'paused',
                }}
                onAnimationEnd={() => {
                  if (isRotating) show(index + 1)
                }}
              />
            </div>
          )}
        </div>

        {slides.length > 1 && (
          <div className="mt-2 flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={t('home.headline.previous')}
              onPress={() => show(index - 1)}
            >
              <ChevronLeftIcon aria-hidden />
            </Button>
            <Button variant="ghost" size="icon-sm" aria-label={t('home.headline.next')} onPress={() => show(index + 1)}>
              <ChevronRightIcon aria-hidden />
            </Button>
            <div className="flex items-center">
              {slides.map((item, position) => (
                // Görünen nokta küçüktür; dokunma alanı (p-2) 24 pikselin üzerindedir (WCAG 2.5.8).
                <button
                  key={item.id}
                  type="button"
                  aria-label={t('home.headline.show', { index: position + 1 })}
                  aria-current={position === index ? 'true' : undefined}
                  onClick={() => show(position)}
                  className="rounded-full p-2 outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                >
                  <span
                    className={cn(
                      'block h-2 rounded-full transition-all motion-reduce:transition-none',
                      position === index ? 'w-6 bg-primary' : 'w-2 bg-muted-foreground/40',
                    )}
                  />
                </button>
              ))}
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="ml-auto"
              aria-label={isPaused ? t('home.headline.playLabel') : t('home.headline.pauseLabel')}
              onPress={() => setPaused((paused) => !paused)}
            >
              {isPaused ? <PlayIcon aria-hidden /> : <PauseIcon aria-hidden />}
              {isPaused ? t('home.headline.play') : t('home.headline.pause')}
            </Button>
          </div>
        )}
      </div>

      {/*
        Geniş ekranda manşetteki haberlerin listesi; gösterilen haber işaretlidir. Liste görselin boyunu aşmaz:
        h-0 + min-h-full ile satırın yüksekliğini sol taraf (görsel) belirler, liste o yüksekliğe sığar. Sığmayan
        son haberler alttaki solma ile kesilir; hepsine noktalardan ve oklardan da ulaşılır.
      */}
      <ol
        aria-label={t('home.headline.list')}
        className="hidden divide-y divide-border overflow-hidden mask-b-from-85% lg:block lg:h-0 lg:min-h-full"
      >
        {slides.map((item, position) => (
          <li
            key={item.id}
            lang={item.language}
            className={cn(
              'border-l-2 py-2.5 pl-4 transition-colors',
              position === index ? 'border-primary' : 'border-transparent',
            )}
          >
            <p className="text-xs text-muted-foreground">
              {item.source.name}
              <span aria-hidden> · </span>
              <time dateTime={item.publishedAt}>{formatPublishedAt(item.publishedAt, locale)}</time>
            </p>
            <Link
              to={`/articles/${item.id}`}
              className={cn(
                'mt-1 line-clamp-2 font-heading text-[0.95rem] leading-snug font-semibold decoration-1 underline-offset-4 hover:underline',
                position !== index && 'text-muted-foreground',
              )}
            >
              {item.title}
            </Link>
          </li>
        ))}
      </ol>
    </section>
  )
}

/**
 * Manşetteki bir haber: büyük görsel, üzerinde karartılmış alt kısımda etiket, kaynak, zaman ve başlık. Beyaz yazı
 * koyu geçişin üzerindedir; iki temada da okunur. Görünmeyen haberler odaklanamaz ve ekran okuyucuya okunmaz (inert).
 */
function Slide({
  item,
  position,
  count,
  isActive,
}: {
  item: ArticleSearchItem
  position: number
  count: number
  isActive: boolean
}) {
  const { t } = useTranslation()
  const { locale } = useLocale()

  return (
    <div
      role="group"
      aria-roledescription={t('home.headline.slide')}
      aria-label={t('home.headline.position', { index: position + 1, count })}
      aria-hidden={!isActive}
      inert={!isActive}
      lang={item.language}
      className="relative w-full shrink-0"
    >
      <div className="relative aspect-[16/9] bg-muted">
        {item.image && (
          <img
            src={item.image.url}
            alt=""
            width={item.image.width}
            height={item.image.height}
            // İlk haber hemen görünür; diğerleri sırası gelmeden indirilmez.
            loading={position === 0 ? 'eager' : 'lazy'}
            decoding="async"
            className="size-full object-cover"
          />
        )}
        <div className="absolute inset-x-0 bottom-0 bg-linear-to-t from-black/90 via-black/60 to-transparent px-5 pt-20 pb-5 text-white sm:px-7 sm:pb-6">
          <BreakingBadge categories={item.categories} />
          <p className="mt-2 text-xs text-white/85">
            {item.source.name}
            <span aria-hidden> · </span>
            <time dateTime={item.publishedAt}>{formatPublishedAt(item.publishedAt, locale)}</time>
          </p>
          <h3 className="mt-1.5 font-heading text-xl leading-tight font-semibold sm:text-3xl">
            {/* after:inset-0: bütün görsel tıklanabilir; bağlantının adı yine başlıktır. */}
            <Link
              to={`/articles/${item.id}`}
              className="decoration-1 underline-offset-4 after:absolute after:inset-0 hover:underline"
            >
              {item.title}
            </Link>
          </h3>
        </div>
      </div>
    </div>
  )
}
