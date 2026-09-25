import { Navigate } from 'react-router-dom'

import { useAuth } from '@/features/auth/AuthContext'
import { OrderingPage } from '@/features/ordering/pages/OrderingPage'

// SERVER/KITCHEN_OPERATOR aren't excluded from ordering (everyone can
// order), but their day-to-day job is the kitchen screen, not placing
// their own order -- so that's what they land on instead of the ordering
// page other roles default to.
const KITCHEN_ONLY_ROLES = ['SERVER', 'KITCHEN_OPERATOR']

export function RoleHome() {
  const { employee } = useAuth()

  if (employee && KITCHEN_ONLY_ROLES.includes(employee.role)) {
    return <Navigate to="/kitchen" replace />
  }

  return <OrderingPage />
}
