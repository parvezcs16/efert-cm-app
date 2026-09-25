# Implementation Plan

## Phase 1 - Foundation
- Repository structure
- Docker
- PostgreSQL
- FastAPI
- React/Vite
- configuration
- logging
- error handling
- migrations
- testing foundation

## Phase 2 - Authentication
- employee model
- registration
- allowed domains
- pending verification
- activation
- OTP
- password state
- RBAC

## Phase 3 - Locations and Menu
- locations
- managers
- kitchen stations
- categories
- menu items
- location-specific availability
- internal prices

## Phase 4 - Employee Ordering
- menu browsing
- dine-in
- takeaway
- booking
- order history
- status lifecycle

## Phase 5 - Kitchen
- station queues
- FIFO priority
- realtime WebSocket updates
- preparation
- ready
- served
- direct server serving

## Phase 6 - Guests
- guest records
- guest history
- sessions
- QR
- multiple active sessions
- independent ordering
- private/official separation

## Phase 7 - Booked Order Management
- ingredient confirmation
- manager alert
- delay response
- serving-time updates
- queue release

## Phase 8 - Consumption and Billing
- served quantities
- employee validation requests
- server validation
- ledger
- private guest charges
- official billing
- adjustments/reversals
- statements

## Phase 9 - Reviews and Notifications
- review system
- anonymity
- configurable categories
- email notifications
- statement schedules

## Phase 10 - Reporting and Hardening
- management reports
- reconciliation
- audit reports
- security hardening
- performance testing
- backup/recovery
- production deployment

## Claude Code workflow
Implement one phase at a time.

For each phase:
1. Inspect current code.
2. Read relevant docs.
3. Plan changes.
4. Implement.
5. Add tests.
6. Run lint/type/test checks.
7. Run migrations if needed.
8. Update documentation.
9. Do not implement future phases unless required by dependencies.
