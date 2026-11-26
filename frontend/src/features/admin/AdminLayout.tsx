import { useQuery } from '@tanstack/react-query'
import { cn } from 'cn'
import {
  EyeOffIcon,
  HistoryIcon,
  LayoutDashboardIcon,
  type LucideIcon,
  RssIcon,
  ScrollTextIcon,
  UsersIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { NavLink, Outlet } from 'react-router'
import { fetchAdminUsers } from '../../api/adminUsers'
import { useAccessToken } from '../../auth/accessToken'
import { useCurrentUser } from '../../auth/currentUser'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  /** Yalnızca bu adreste seçili görünsün (pano: diğer ekranların adresi de /admin ile başlar). */
  end?: boolean
}

/**
 * Yönetim panelinin çerçevesi: yan menü (Pano, Kullanıcılar, Kaynaklar, Toplama geçmişi, Gizlenen haberler, Audit
 * kayıtları) ve seçili ekran (ekran akışları 3. bölüm). Dar ekranda menü ekranın üstünde yatay durur.
 *
 * Yönetici olmayan kullanıcıya (adresi elle yazdıysa) içerik gösterilmez ve ekranlar API'ye hiç sormaz.
 * Bu yalnızca bir kolaylıktır; asıl yetki kontrolü backend'dedir.
 */
export function AdminLayout() {
  const { t } = useTranslation()
  const currentUser = useCurrentUser()

  if (currentUser.role !== 'ADMIN') {
    return <p className="px-4 py-10 text-muted-foreground sm:px-6">{t('admin.noPermission')}</p>
  }

  // Simgeler ekranın işini anlatır: pano kutucukları, kişiler, RSS beslemeleri, geçmiş, gizleme (haber
  // detayındaki "Gizle" düğmesiyle aynı simge) ve kayıt defteri.
  const items: NavItem[] = [
    { to: '/admin', label: t('admin.nav.dashboard'), icon: LayoutDashboardIcon, end: true },
    { to: '/admin/users', label: t('admin.nav.users'), icon: UsersIcon },
    { to: '/admin/sources', label: t('admin.nav.sources'), icon: RssIcon },
    { to: '/admin/ingestion-runs', label: t('admin.nav.runs'), icon: HistoryIcon },
    { to: '/admin/hidden-articles', label: t('admin.nav.hidden'), icon: EyeOffIcon },
    { to: '/admin/audit-events', label: t('admin.nav.audit'), icon: ScrollTextIcon },
  ]

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    cn(
      'flex items-center gap-2.5 rounded-md px-3 py-2 text-base transition-colors hover:bg-muted',
      isActive ? 'bg-muted font-medium text-foreground' : 'text-muted-foreground',
    )

  // Panel geniş ekranı kullanır; çok geniş ekranda (2xl) sağda da soldaki menü alanı kadar boşluk bırakılır
  // (menü 13rem + aralık 2.5rem + kenar 1.5rem = 17rem): içerik dengeli durur, satırlar aşırı uzamaz.
  return (
    <div className="grid gap-6 px-4 py-8 sm:px-6 sm:py-10 md:grid-cols-[13rem_minmax(0,1fr)] md:gap-10 2xl:pr-68">
      <nav aria-label={t('admin.nav.label')}>
        <ul className="flex flex-wrap gap-1 md:flex-col">
          {items.map(({ to, label, icon: Icon, end }) => (
            <li key={to}>
              <NavLink to={to} end={end} className={linkClass}>
                <Icon aria-hidden className="size-4 shrink-0" />
                {label}
                {to === '/admin/users' && <PendingUsersBadge />}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <div className="min-w-0">
        <Outlet />
      </div>
    </div>
  )
}

/**
 * Onay bekleyen kullanıcı sayısı. Kullanıcı listesiyle aynı önbellek anahtarı ailesindedir (`admin-users`):
 * bir kullanıcı onaylanınca liste yenilenirken sayı da yenilenir. Bekleyen yoksa hiçbir şey gösterilmez.
 */
function PendingUsersBadge() {
  const { t } = useTranslation()
  const accessToken = useAccessToken()
  const pending = useQuery({
    queryKey: ['admin-users', 'pending-count'],
    queryFn: () => fetchAdminUsers(accessToken, new URLSearchParams({ status: 'PENDING', size: '1' })),
    select: (response) => response.totalElements,
  })

  if (!pending.data) {
    return null
  }
  return (
    <>
      <span
        aria-hidden
        className="ml-auto rounded-full bg-primary px-1.5 py-0.5 text-xs leading-none font-semibold text-primary-foreground tabular-nums"
      >
        {pending.data}
      </span>
      {/* Ekran okuyucu "Kullanıcılar, 2 onay bekleyen" okur; görünen sayı tek başına anlamsız kalırdı. */}
      <span className="sr-only">, {t('admin.nav.pendingCount', { count: pending.data })}</span>
    </>
  )
}
