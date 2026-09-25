import type { EmployeeRole } from '@/lib/types'

export const KITCHEN_STAFF_ROLES: EmployeeRole[] = [
  'SERVER',
  'KITCHEN_OPERATOR',
  'LOCATION_MANAGER',
  'SYSTEM_MANAGER',
  'SYSTEM_ADMINISTRATOR',
]

export const ADMIN_ROLES: EmployeeRole[] = [
  'LOCATION_MANAGER',
  'SYSTEM_MANAGER',
  'SYSTEM_ADMINISTRATOR',
  'FINANCE_ADMIN',
]

export const SYSTEM_LEVEL_ROLES: EmployeeRole[] = ['SYSTEM_MANAGER', 'SYSTEM_ADMINISTRATOR']

export function hasRole(role: EmployeeRole | undefined, allowed: EmployeeRole[]): boolean {
  return !!role && allowed.includes(role)
}
