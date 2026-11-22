import type { UserStatus } from './me'
import { apiGet } from './client'

export type ComponentStatus = 'UP' | 'DOWN'

/** Yönetim panosunun verisi (API sözleşmesi 6.7; FG-YP-12). */
export interface Stats {
  articles: {
    total: number
    /** Son 24 saatte toplanan haberler. */
    last24h: number
    /** Bütün kaynaklar, ada göre; haberi olmayan kaynak 0 ile gelir. */
    bySource: { code: string; name: string; total: number; last24h: number }[]
  }
  users: Record<UserStatus, number>
  feeds: {
    /** Okunan beslemeler: kendisi ve kaynağı etkin. */
    enabled: number
    /** Okunan beslemelerden son okuması başarısız olanlar. */
    failing: number
    /** Art arda hatalar yüzünden kendiliğinden kapananlar. */
    disabledAuto: number
  }
  searchIndex: {
    /** Elasticsearch'e henüz aktarılmamış değişiklikler. */
    pendingOutboxEvents: number
  }
  components: {
    database: ComponentStatus
    elasticsearch: ComponentStatus
    objectStorage: ComponentStatus
    /** İşçinin en son başlattığı toplama; hiç toplama yoksa `null`. */
    workerLastActivityAt: string | null
  }
}

export function fetchStats(accessToken: string): Promise<Stats> {
  return apiGet<Stats>('/api/v1/admin/stats', accessToken)
}
