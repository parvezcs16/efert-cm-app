import { NavLink, Outlet, useNavigate } from 'react-router-dom'

import { BrandLogo, BrandStripe } from '@/components/BrandLogo'
import { NotificationBell } from '@/components/NotificationBell'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/AuthContext'
import { hasRole, KITCHEN_STAFF_ROLES, ADMIN_ROLES } from '@/lib/roles'
import { cn } from '@/lib/utils'

const baseLinks = [
  { to: '/order', label: 'Order' },
  { to: '/orders', label: 'My Orders' },
  { to: '/guests', label: 'Guests' },
  { to: '/billing', label: 'Billing' },
  { to: '/reviews', label: 'Reviews' },
]

export function AppLayout() {
  const { employee, logout } = useAuth()
  const navigate = useNavigate()

  const links = [
    ...baseLinks,
    ...(hasRole(employee?.role, KITCHEN_STAFF_ROLES) ? [{ to: '/kitchen', label: 'Kitchen' }] : []),
    ...(hasRole(employee?.role, ADMIN_ROLES) ? [{ to: '/admin', label: 'Admin' }] : []),
  ]

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex min-h-svh flex-col">
      <header className="sticky top-0 z-10 border-b bg-card/95 backdrop-blur">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2">
          <NavLink to="/" aria-label="Home">
            <BrandLogo />
          </NavLink>
          <nav className="flex flex-wrap items-center gap-x-1 gap-y-1 text-sm">
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === '/order'}
                className={({ isActive }) =>
                  cn(
                    'rounded-md px-3 py-1.5 text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                    isActive && 'bg-accent font-medium text-primary',
                  )
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm">
            <NotificationBell />
            <span className="text-muted-foreground">
              {employee?.name} ({employee?.p_no})
            </span>
            <Button variant="outline" size="sm" onClick={handleLogout}>
              Sign out
            </Button>
          </div>
        </div>
        <BrandStripe />
      </header>
      <main className="flex-1 p-4">
        <Outlet />
      </main>
    </div>
  )
}
