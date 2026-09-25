// Mirrors backend/app/models/enums.py and the schemas that expose them.
// Kept as plain string unions (not TS enums) to match how they serialize
// over JSON.

export type EmployeeRole =
  | 'EMPLOYEE'
  | 'SERVER'
  | 'KITCHEN_OPERATOR'
  | 'LOCATION_MANAGER'
  | 'SYSTEM_MANAGER'
  | 'FINANCE_ADMIN'
  | 'SYSTEM_ADMINISTRATOR'

export type EmployeeStatus = 'PENDING_ACTIVATION' | 'ACTIVE' | 'SUSPENDED' | 'INACTIVE'
export type PasswordState = 'MUST_CHANGE' | 'OK'
export type StatementFrequency = 'DAILY' | 'WEEKLY' | 'BIWEEKLY' | 'MONTHLY'

export interface Employee {
  id: string
  p_no: string
  name: string
  email: string
  department: string | null
  status: EmployeeStatus
  role: EmployeeRole
  password_state: PasswordState
  statement_frequency: StatementFrequency
  next_statement_due_at: string | null
  created_at: string
}

export type ActiveStatus = 'ACTIVE' | 'INACTIVE'

export interface Location {
  id: string
  name: string
  code: string
  status: ActiveStatus
  manager_id: string | null
}

export interface KitchenStation {
  id: string
  location_id: string
  name: string
  status: ActiveStatus
}

export interface MenuCategory {
  id: string
  location_id: string
  name: string
  display_order: number
  status: ActiveStatus
}

export interface MenuItem {
  id: string
  category_id: string
  name: string
  description: string | null
  status: ActiveStatus
}

export interface MenuItemLocation {
  id: string
  menu_item_id: string
  location_id: string
  is_available: boolean
  price: string
  effective_from: string | null
  effective_to: string | null
}

export interface MenuBrowseItem {
  id: string
  name: string
  description: string | null
}

export interface MenuBrowseCategory {
  id: string
  name: string
  display_order: number
  items: MenuBrowseItem[]
}

export type OrderType = 'DINE_IN' | 'TAKEAWAY' | 'BOOK_FOR_LATER'
export type OrderStatus =
  | 'PENDING'
  | 'CONFIRMED'
  | 'QUEUED'
  | 'PREPARING'
  | 'READY'
  | 'SERVED'
  | 'CANCELLED'
export type CustomerType = 'EMPLOYEE' | 'GUEST'
export type IngredientStatus = 'PENDING' | 'CONFIRMED' | 'DELAYED'

export interface OrderItem {
  id: string
  menu_item_id: string
  ordered_quantity: number
  kitchen_station_id: string | null
}

export interface Order {
  id: string
  order_number: string
  location_id: string
  customer_type: CustomerType
  order_type: OrderType
  scheduled_for: string | null
  status: OrderStatus
  ingredient_status: IngredientStatus | null
  ingredient_response_message: string | null
  created_at: string
  items: OrderItem[]
}

export type GuestType = 'PRIVATE' | 'OFFICIAL'
export type GuestSessionStatus = 'ACTIVE' | 'CLOSED'

export interface Guest {
  id: string
  host_employee_id: string
  name: string
  company_name: string
  cnic: string
  guest_type: GuestType
  accompanying_persons: number
  created_at: string
}

export interface GuestSession {
  id: string
  guest_id: string
  host_employee_id: string
  status: GuestSessionStatus
  opened_at: string
  closed_at: string | null
  token_expires_at: string
}

export type ConsumptionStatus = 'VALIDATED' | 'CORRECTION_REQUESTED'

export interface ConsumptionRecord {
  id: string
  order_item_id: string
  served_quantity: number
  status: ConsumptionStatus
  served_at: string
  requested_quantity: number | null
  requested_reason: string | null
}

export type LedgerSourceType = 'PERSONAL_CONSUMPTION' | 'PRIVATE_GUEST' | 'OFFICIAL_GUEST'
export type LedgerEntryType = 'DEBIT' | 'CREDIT'

export interface LedgerEntry {
  id: string
  source_type: LedgerSourceType
  entry_type: LedgerEntryType
  amount: string
  reason: string
  guest_session_id: string | null
  created_at: string
}

export interface Statement {
  entries: LedgerEntry[]
  total_debit: string
  total_credit: string
  net_balance: string
}

export type ReviewType = 'OVERALL' | 'ORDER'

export interface ReviewCategory {
  id: string
  location_id: string | null
  name: string
  enabled: boolean
  is_manager_defined: boolean
}

export interface ReviewCategoryRating {
  category_id: string
  rating: number
}

export interface Review {
  id: string
  location_id: string
  employee_id: string | null
  is_anonymous: boolean
  review_type: ReviewType
  order_id: string | null
  overall_rating: number
  comment: string | null
  created_at: string
  category_ratings: ReviewCategoryRating[]
}

export interface AuditLogEntry {
  id: string
  actor_employee_id: string | null
  action: string
  entity_type: string
  entity_id: string | null
  old_values: Record<string, unknown> | null
  new_values: Record<string, unknown> | null
  created_at: string
}

export interface SalesSummary {
  location_id: string
  since: string
  until: string
  total_orders: number
  orders_by_status: Record<string, number>
  orders_by_type: Record<string, number>
  total_revenue: string
}

export interface ReconciliationLine {
  order_id: string
  order_number: string
  order_item_id: string
  menu_item_id: string
  ordered_quantity: number
  served_quantity: number
  expected_amount: string
  billed_amount: string
  matches: boolean
}

export interface ReconciliationReport {
  location_id: string
  since: string
  until: string
  lines: ReconciliationLine[]
  mismatch_count: number
}
