import { cn } from 'cn'
import { useTranslation } from 'react-i18next'
import { NavLink, Outlet } from 'react-router'
import { useCurrentUser } from '../../auth/currentUser'

/**
 * Yönetim panelinin çerçevesi: yan menü (Pano, Kullanıcılar, Kaynaklar, Toplama geçmişi, Audit kayıtları) ve seçili ekran
 * (ekran akışları 3. bölüm). Dar ekranda menü ekranın üstünde yatay durur.
 *
 * Yönetici olmayan kullanıcıya (adresi elle yazdıysa) içerik gösterilmez ve ekranlar API'ye hiç sormaz.
 * Bu yalnızca bir kolaylıktır; asıl yetki kontrolü backend'dedir.
 */
export function AdminLayout() {
  const { t } = useTranslation()
  const currentUser = useCurrentUser()

  if (currentUser.role !== 'ADMIN') {
    return <p className="mx-auto max-w-6xl px-4 py-10 text-muted-foreground sm:px-6">{t('admin.noPermission')}</p>
  }

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    cn(
      'block rounded-md px-3 py-2 text-base transition-colors hover:bg-muted',
      isActive ? 'bg-muted font-medium text-foreground' : 'text-muted-foreground',
    )

  return (
    <div className="mx-auto grid max-w-6xl gap-6 px-4 py-8 sm:px-6 sm:py-10 md:grid-cols-[13rem_minmax(0,1fr)] md:gap-10">
      <nav aria-label={t('admin.nav.label')}>
        <ul className="flex flex-wrap gap-1 md:flex-col">
          <li>
            {/* end: "/admin" yalnızca panodayken seçili görünür; diğer ekranların adresi de onunla başlar. */}
            <NavLink to="/admin" end className={linkClass}>
              {t('admin.nav.dashboard')}
            </NavLink>
          </li>
          <li>
            <NavLink to="/admin/users" className={linkClass}>
              {t('admin.nav.users')}
            </NavLink>
          </li>
          <li>
            <NavLink to="/admin/sources" className={linkClass}>
              {t('admin.nav.sources')}
            </NavLink>
          </li>
          <li>
            <NavLink to="/admin/ingestion-runs" className={linkClass}>
              {t('admin.nav.runs')}
            </NavLink>
          </li>
          <li>
            <NavLink to="/admin/audit-events" className={linkClass}>
              {t('admin.nav.audit')}
            </NavLink>
          </li>
        </ul>
      </nav>
      <div className="min-w-0">
        <Outlet />
      </div>
    </div>
  )
}
