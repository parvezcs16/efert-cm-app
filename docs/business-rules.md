# Business Rules

## Billing Responsibility
PRIVATE guest -> host employee personal mess ledger.
OFFICIAL guest -> official guest billing only.

Private guest charges must remain separately identifiable even when included
in the host's consolidated personal + private guest total.

## Served Quantity
Ordered quantity is not automatically billable.

Billable quantity = validated served quantity.

Server validation is required when an employee changes served quantity.

## Financial Corrections
Never mutate/delete historical financial transactions.
Create:
- adjustment
- reversal
- correction reference
- actor
- timestamp
- reason

## Order Priority
1. Immediate orders
2. Booked orders that have been confirmed and released into the queue

Within the same priority, use FIFO unless an explicit operational rule overrides it.

Booked orders do not outrank immediate orders.

## Booked Orders
A booked order is visible to management/kitchen immediately.

Ingredient availability must be confirmed.

If ingredients are unavailable, management can delay the serving time and provide
a response to the employee.

Once confirmed, the order becomes eligible for the active kitchen queue.

## Guest Sessions
One guest may have multiple historical sessions.
A host may have multiple active guest sessions.

Closing a session stops normal new-session activity but QR invalidation is
delayed according to the 24-hour rule.

## Menu Availability
Menu availability is location-specific.

Prices are location-specific internal data.

Employees should see the sellable menu item and ordering information, but not
internal pricing/cost configuration where the business requires prices hidden.

## Reviews
Overall mess reviews can be submitted multiple times.
A review can be anonymous or identified.
Categories/questions can be system-defined and optionally manager-configurable.
