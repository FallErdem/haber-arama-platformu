import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { cn } from 'cn'
import { useState } from 'react'
import type { Key } from 'react-aria-components'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router'
import { fetchAdminUsers } from '../../../api/adminUsers'
import { useAccessToken } from '../../../auth/accessToken'
import { Button } from '../../../components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select'
import { Pagination } from '../../search/Pagination'
import { SearchBox } from '../../search/SearchBox'
import {
  parseAdminUsersState,
  toApiParams,
  toUrlParams,
  USER_ROLES,
  USER_STATUSES,
  type AdminUsersState,
} from './adminUsersState'
import { UserRow } from './UserRow'

/** Filtre seçimlerinde "hepsi" seçeneğinin kimliği; adrese yazılmaz. */
const ALL = 'ALL'

/**
 * Yönetim paneli: Kullanıcılar (ekran akışları 5.2; FG-YP-01 – 03). Yönetici olmayan kullanıcıyı yönetim
 * panelinin çerçevesi (AdminLayout) durdurur.
 */
export function AdminUsersPage() {
  const { t } = useTranslation()
  const accessToken = useAccessToken()
  const [params, setParams] = useSearchParams()
  const state = parseAdminUsersState(params)
  const [actionMessage, setActionMessage] = useState<string | null>(null)

  // Filtre veya arama değişince ilk sayfaya dönülür.
  const update = (changes: Partial<AdminUsersState>) => setParams(toUrlParams({ ...state, page: 1, ...changes }))
  const hrefForPage = (page: number) => `?${toUrlParams({ ...state, page }).toString()}`

  const apiQuery = toApiParams(state).toString()
  const users = useQuery({
    queryKey: ['admin-users', apiQuery],
    queryFn: () => fetchAdminUsers(accessToken, new URLSearchParams(apiQuery)),
    placeholderData: keepPreviousData,
  })

  return (
    <div>
      <h1 className="mb-5 text-3xl font-semibold tracking-tight">{t('admin.users.title')}</h1>
      <SearchBox
        key={state.q}
        query={state.q}
        onSearch={(q) => update({ q })}
        label={t('admin.users.searchLabel')}
        placeholder={t('admin.users.searchPlaceholder')}
      />
      <div className="mt-3 flex flex-wrap gap-2">
        <SingleFilter
          label={t('admin.users.statusFilter')}
          allLabel={t('admin.users.allStatuses')}
          value={state.status}
          options={USER_STATUSES.map((status) => ({ id: status, name: t(`userStatuses.${status}`) }))}
          onChange={(status) => update({ status: USER_STATUSES.find((option) => option === status) })}
        />
        <SingleFilter
          label={t('admin.users.roleFilter')}
          allLabel={t('admin.users.allRoles')}
          value={state.role}
          options={USER_ROLES.map((role) => ({ id: role, name: t(`userRoles.${role}`) }))}
          onChange={(role) => update({ role: USER_ROLES.find((option) => option === role) })}
        />
      </div>

      {/* İşlem hataları tek yerde, listenin üstünde duyurulur (son yönetici, sürüm çakışması). */}
      {actionMessage && (
        <p role="alert" className="mt-6 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm">
          {actionMessage}
        </p>
      )}

      {users.isPending ? (
        <p className="mt-10 text-muted-foreground">{t('admin.users.loading')}</p>
      ) : users.isError ? (
        <div role="alert" className="mt-10">
          <p>{t('admin.users.loadFailed')}</p>
          <Button variant="outline" className="mt-4" onPress={() => void users.refetch()}>
            {t('admin.users.retry')}
          </Button>
        </div>
      ) : users.data.items.length === 0 ? (
        <p className="py-16 text-center text-muted-foreground">{t('admin.users.empty')}</p>
      ) : (
        <>
          <ul
            aria-busy={users.isFetching}
            className={cn(
              'mt-6 divide-y divide-border border-t border-border transition-opacity',
              users.isPlaceholderData && 'opacity-50',
            )}
          >
            {users.data.items.map((user) => (
              <li key={user.id}>
                <UserRow user={user} onResult={setActionMessage} />
              </li>
            ))}
          </ul>
          <Pagination page={state.page} totalPages={users.data.totalPages} hrefForPage={hrefForPage} />
        </>
      )}
    </div>
  )
}

/** Tek seçimli filtre; "hepsi" seçeneği filtreyi kaldırır. */
function SingleFilter({
  label,
  allLabel,
  value,
  options,
  onChange,
}: {
  label: string
  allLabel: string
  value: string | undefined
  options: { id: string; name: string }[]
  onChange: (value: string | undefined) => void
}) {
  return (
    <Select
      aria-label={label}
      value={value ?? ALL}
      onChange={(key: Key | null) => onChange(key === null || key === ALL ? undefined : String(key))}
    >
      <SelectTrigger className={cn('w-auto', value && 'border-primary text-primary')}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem id={ALL}>{allLabel}</SelectItem>
        {options.map((option) => (
          <SelectItem key={option.id} id={option.id}>
            {option.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
