# Ordering

## Types
- DINE_IN
- TAKEAWAY
- BOOK_FOR_LATER

## Sources
- Employee
- Guest QR
- Server

## Rules
Employee and guest orders remain separate.

One order can contain multiple order items and quantities.

OrderItem stores the historical unit-price snapshot internally.

Employee-facing UI should not expose internal price configuration.

## Lifecycle
PENDING
-> CONFIRMED
-> QUEUED
-> PREPARING
-> READY
-> SERVED

Cancellation is permitted before serving.

## Walk-up orders
A server can create an order for an employee or guest.
The order can follow the kitchen queue or be marked served directly when
operationally appropriate and authorized.

## Scheduled orders
Booked orders are visible immediately.
They require ingredient confirmation.
After confirmation they can enter the active queue.
Immediate orders retain higher priority.
