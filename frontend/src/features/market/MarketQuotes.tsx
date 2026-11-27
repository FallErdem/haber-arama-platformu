import { useQuery } from '@tanstack/react-query'
import { useLocale } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { fetchMarketQuotes, type MarketQuote } from '../../api/marketQuotes'
import { useAccessToken } from '../../auth/accessToken'

/**
 * Kutuda gösterilen değerler ve sırası (geniş ekranda 4×2: üstte döviz ve altın, altta gümüş, borsa, petrol ve
 * Bitcoin). API bunların dışında bir kod döndürürse gösterilmez.
 */
const DISPLAY_ORDER = ['USD', 'EUR', 'GRAM_GOLD', 'GOLD_OUNCE', 'SILVER_OUNCE', 'BIST100', 'BRENT', 'BITCOIN']

/** İşçi değerleri 15 dakikada bir günceller; kutu 5 dakikada bir sorar, yeni değer en geç 5 dakikada görünür. */
const REFRESH_INTERVAL_MS = 5 * 60_000

/**
 * Arama kutusunun sağındaki piyasa kutusu (issue #79): döviz, altın, gümüş, BIST 100, Brent petrol ve Bitcoin,
 * önceki kapanışa göre değişimleriyle. Yüklenirken, hata olursa veya henüz değer yoksa kutu hiç görünmez; sayfanın geri kalanı
 * etkilenmez.
 */
export function MarketQuotes() {
  const { t } = useTranslation()
  const { locale } = useLocale()
  const accessToken = useAccessToken()
  const quotes = useQuery({
    queryKey: ['market-quotes'],
    queryFn: () => fetchMarketQuotes(accessToken),
    staleTime: REFRESH_INTERVAL_MS,
    refetchInterval: REFRESH_INTERVAL_MS,
  })

  if (!quotes.isSuccess) {
    return null
  }
  const byCode = new Map(quotes.data.map((quote) => [quote.code, quote]))
  const shown = DISPLAY_ORDER.flatMap((code) => byCode.get(code) ?? [])
  if (shown.length === 0) {
    return null
  }

  // Değerler farklı turlarda yazılmış olabilir (okunamayan değer eski kalır); en yeni çekim zamanı gösterilir.
  const lastFetchedAt = new Date(Math.max(...shown.map((quote) => Date.parse(quote.fetchedAt))))
  const price = new Intl.NumberFormat(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  // Yüzde biçimi dile göre: Türkçede "%0,13", İngilizcede "0.13%".
  const percent = new Intl.NumberFormat(locale, {
    style: 'percent',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
  const time = new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit' })

  return (
    // h-full: kutu, soldaki başlık, arama kutusu ve filtrelerle aynı yükseklikte durur; alt satır en alta iner.
    <section
      aria-labelledby="market-quotes-title"
      className="@container flex h-full flex-col justify-between gap-3 rounded-md border border-border bg-card p-4"
    >
      <h2 id="market-quotes-title" className="sr-only">
        {t('market.title')}
      </h2>
      {/* Sütunların genişliği içeriğe göredir (auto) ve aralarındaki boşluk eşit dağıtılır (justify-between): ilk sütun
          soldan, son sütun sağdan kutunun iç boşluğu kadar içeride durur. Sütun sayısı ekranın değil kutunun
          iç genişliğine göre seçilir (@container): 384 px'ten genişse 4, 256 px'ten genişse 3, daha darsa 2. */}
      <dl className="grid grid-cols-[repeat(2,auto)] justify-between gap-x-4 gap-y-3 @3xs:grid-cols-[repeat(3,auto)] @sm:grid-cols-[repeat(4,auto)]">
        {shown.map((quote) => (
          <QuoteItem key={quote.code} quote={quote} price={price} percent={percent} />
        ))}
      </dl>
      <p className="text-xs text-muted-foreground">
        {t('market.updatedAt', { time: time.format(lastFetchedAt) })} · {t('market.source')}
      </p>
    </section>
  )
}

function QuoteItem({
  quote,
  price,
  percent,
}: {
  quote: MarketQuote
  price: Intl.NumberFormat
  percent: Intl.NumberFormat
}) {
  const { t } = useTranslation()
  const direction = quote.changePercent > 0 ? 'up' : quote.changePercent < 0 ? 'down' : 'flat'

  return (
    // <dl> içinde <div>: bir adı (dt) ve değerlerini (dd) birlikte gruplar; HTML buna izin verir.
    <div className="min-w-0">
      <dt className="truncate text-xs text-muted-foreground">{t(`market.names.${quote.code}`)}</dt>
      <dd className="text-sm font-semibold tabular-nums">
        {/* Ons altın, ons gümüş, Brent ve Bitcoin dolar cinsindendir; TL olanlarda simge yoktur. */}
        {quote.currency === 'USD' && '$'}
        {price.format(quote.price)}
      </dd>
      <dd
        className={
          direction === 'up'
            ? 'text-xs text-success tabular-nums'
            : direction === 'down'
              ? 'text-xs text-destructive tabular-nums'
              : 'text-xs text-muted-foreground tabular-nums'
        }
      >
        {/* Ok yalnızca görseldir; ekran okuyucu yönü kelimeyle okur. Renk de tek başına anlam taşımaz. */}
        {direction !== 'flat' && (
          <>
            <span aria-hidden>{direction === 'up' ? '▲ ' : '▼ '}</span>
            <span className="sr-only">{t(`market.${direction}`)} </span>
          </>
        )}
        {percent.format(Math.abs(quote.changePercent) / 100)}
      </dd>
    </div>
  )
}
