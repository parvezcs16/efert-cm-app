# Consumption

Consumption represents food actually served.

Example:
Ordered = 3
Served = 2
Consumption = 2

## Quantity Correction
Employee can request/change the served quantity.
Server validates the quantity.

The validated quantity is used for billing.

## Returned Food
If food is returned after serving:
- Do not erase the original transaction.
- Create a return/correction/reversal record.
- Maintain who performed the action and why.

## Audit
Every correction should record:
- actor
- original quantity
- corrected quantity
- reason
- timestamp
- related order item
