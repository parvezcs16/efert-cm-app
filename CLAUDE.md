# Central Mess Management System

## Purpose
A multi-location central mess platform for employee ordering, guest ordering,
kitchen operations, consumption tracking, employee mess ledgers, official
guest billing, notifications, reviews, and administration.

## Technology
- Backend: Python 3.12, FastAPI, SQLAlchemy 2.x, Pydantic v2, Alembic
- Database: PostgreSQL
- Frontend: React + TypeScript + Vite
- UI: Tailwind CSS + shadcn/ui
- Realtime: WebSockets
- Deployment: Docker + Nginx
- Architecture: Modular monolith

Do not introduce microservices unless explicitly requested.

## Core Principles
1. Backend is the source of truth.
2. Keep API routes thin; business logic belongs in services.
3. Ordering, consumption, and billing are separate domains.
4. Historical financial records must be immutable; use adjustments/reversals.
5. Served quantity, not merely ordered quantity, determines consumption billing.
6. All important state changes must be auditable.
7. Design for multiple mess locations and multiple kitchen stations.
8. Employees may order from any location.
9. Never expose internal prices/cost rules to employees unless explicitly required.
10. Prefer database constraints and transactions for critical business rules.

## Authentication
Employee identity is based on P-Number.

Self-registration:
- P-Number and company email are required.
- Email must belong to an allowed company domain.
- Registration remains PENDING until verification/approval.
- Admin-created employees are also supported.

Activation:
P-Number/password -> OTP -> mandatory password change -> application access.

Password reset/change:
- OTP is required.
- Do not allow protected application routes until required password state is satisfied.

OTP should use industry-standard expiry/rate limits and never store plaintext OTPs.

## Guests
Guest types:
- PRIVATE
- OFFICIAL

Guest registration requires:
- Name
- Company name
- CNIC
- Number of accompanying persons

A guest is associated with a host employee.

Guests do not need permanent employee accounts.
A guest receives a temporary signed QR/session token.

A guest session:
- Can support multiple orders.
- Can be closed by the host.
- Can later be reopened for the same guest.
- QR access does not immediately become invalid on close; access is fully invalidated after 24 hours according to the business rules.
- Historical guest sessions remain linked to the guest.

Private guest:
- Consumption is charged to host employee's personal mess ledger.
- Private guest transactions remain separately identifiable.

Official guest:
- Consumption remains in official guest billing.
- It must not affect the host employee's personal deduction.
- Official and private guest consumption must remain separately reportable.

## Ordering
Order types:
- DINE_IN
- TAKEAWAY
- BOOK_FOR_LATER

Employee and guest orders are separate orders.

Orders can originate from:
- Employee self-service
- Guest QR self-service
- Server/counter entry

An order can contain multiple items and quantities.

Booked orders enter the booking workflow immediately but have lower kitchen priority than immediate orders.

If ingredients are not confirmed:
- Notify/alert the system manager.
- Manager can return a response/delay time.
- Employee is notified of the response or updated serving time.
- Once ingredients are confirmed, the booked order is placed into the active queue.
- The booking workflow must allow management to verify ingredients before the two-hour threshold.

Immediate orders have priority over booked orders.

## Kitchen
Support multiple kitchen stations.

Kitchen screens show queue state in real time.

Typical lifecycle:
PENDING -> CONFIRMED -> QUEUED -> PREPARING -> READY -> SERVED

Cancellation is allowed before serving.

A server may mark an order served when food is actually handed over.

Direct counter orders may still enter the kitchen queue, but authorized servers may also mark eligible orders served directly.

## Consumption
Billing is created only from actual served consumption.

Example:
Ordered quantity = 3
Served quantity = 2
Billable consumption = 2

Employee may request/change served quantity, but server validation is required before the correction affects billing.

Returned/corrected food must create a correction/reversal record rather than silently changing financial history.

## Billing
Maintain an employee mess ledger.

Maintain separate:
- Personal employee consumption
- Private guest consumption
- Official guest billing

Provide:
- Personal bill
- Private guest bill
- Official guest bill
- Consolidated personal + private guest view

Never delete financial transactions.
Corrections and overbilling use reversal/adjustment entries with audit information.

Prices are internal management data and are hidden from employees in normal ordering UX.

OrderItem stores the effective historical unit price internally.

## Locations
The system supports multiple locations.

Each location has its own:
- Manager/admin
- Menu availability
- Menu pricing
- Kitchen stations
- Operational settings

Employees may order from any location.

## Notifications
Build a notification abstraction so email exists first and SMS/WhatsApp/push
can be added later without changing business logic.

Employee statement frequency:
- DAILY
- WEEKLY
- BIWEEKLY
- MONTHLY

Employee controls their preferred statement frequency.

## Reviews
Review categories include:
- FOOD
- ENVIRONMENT
- HYGIENE
- SERVER_BEHAVIOR

Support:
- Overall mess reviews
- Individual order reviews
- Identified reviews
- Anonymous reviews

Overall mess reviews may be submitted multiple times.

Review categories/questions may be system-defined and optionally manager-configurable.

## Code Quality
- Type hints everywhere practical.
- Explicit domain enums.
- Transaction boundaries around state-changing business operations.
- Unit tests for business services.
- Integration tests for critical database workflows.
- Never trust frontend state for authorization, billing, prices, or served quantities.
