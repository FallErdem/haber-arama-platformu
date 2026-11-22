import { render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { describe, expect, it } from 'vitest'
import type { Me } from '../../api/me'
import { CurrentUserContext } from '../../auth/currentUser'
import { AdminLayout } from './AdminLayout'

const ADMIN: Me = {
  id: '0193f1a2-0000-7000-8000-0000000000a1',
  email: 'yonetici@example.test',
  displayName: 'Yönetici',
  role: 'ADMIN',
  status: 'ACTIVE',
}

function renderAt(path: string, currentUser: Me = ADMIN) {
  render(
    <CurrentUserContext value={currentUser}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/admin" element={<AdminLayout />}>
            <Route path="sources" element={<p>Kaynaklar ekranı</p>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </CurrentUserContext>,
  )
}

describe('AdminLayout', () => {
  it('yöneticiye yan menüyü ve seçili ekranı gösterir; bulunulan ekran menüde işaretlidir', () => {
    renderAt('/admin/sources')

    const menu = screen.getByRole('navigation', { name: 'Yönetim menüsü' })
    const links = within(menu).getAllByRole('link')
    expect(links.map((link) => [link.textContent, link.getAttribute('href')])).toEqual([
      ['Pano', '/admin'],
      ['Kullanıcılar', '/admin/users'],
      ['Kaynaklar', '/admin/sources'],
      ['Toplama geçmişi', '/admin/ingestion-runs'],
      ['Gizlenen haberler', '/admin/hidden-articles'],
      ['Audit kayıtları', '/admin/audit-events'],
    ])
    expect(within(menu).getByRole('link', { name: 'Kaynaklar' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByText('Kaynaklar ekranı')).toBeInTheDocument()
  })

  it('yönetici olmayan kullanıcıya menüyü ve ekranı göstermez; ekran çizilmediği için API isteği de gitmez', () => {
    renderAt('/admin/sources', { ...ADMIN, role: 'USER' })

    expect(screen.getByText('Bu sayfayı görüntüleme yetkiniz yok.')).toBeInTheDocument()
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument()
    expect(screen.queryByText('Kaynaklar ekranı')).not.toBeInTheDocument()
  })
})
