import { apiGet } from './client'

/**
 * Bir piyasa değeri (issue #79). Görünen adı yanıtta yoktur; arayüz dil dosyalarından koda göre bulur.
 * Değerleri işçi 15 dakikada bir Yahoo Finance'ten çeker; API tablodan okur.
 */
export interface MarketQuote {
  /** `USD`, `EUR`, `GRAM_GOLD`, `GOLD_OUNCE`, `SILVER_OUNCE`, `BIST100`, `BRENT` veya `BITCOIN`. */
  code: string
  price: number
  /** Önceki kapanışa göre değişim yüzdesi: `0.13` = %0,13, `-1.64` = −%1,64. */
  changePercent: number
  /** Fiyatın para birimi: `TRY` veya `USD`. */
  currency: string
  /** Piyasadaki son fiyatın zamanı. */
  marketTime: string
  /** İşçinin değeri çektiği zaman. */
  fetchedAt: string
}

/** Bütün değerler; işçi henüz hiç çekmediyse boş liste. */
export async function fetchMarketQuotes(accessToken: string): Promise<MarketQuote[]> {
  return (await apiGet<{ items: MarketQuote[] }>('/api/v1/market-quotes', accessToken)).items
}
