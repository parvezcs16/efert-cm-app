# Database Specification

## Core entities

### Employee
- id
- p_no
- name
- email
- department
- status
- password state
- timestamps

### EmployeeRegistration
- id
- employee/p-number reference
- email
- status
- verification metadata
- timestamps

### Location
- id
- name
- code
- status
- manager relationship
- timestamps

### Guest
- id
- host employee id
- name
- company name
- CNIC
- guest type
- history/status
- timestamps

### GuestSession
- id
- guest id
- host employee id
- signed token/session identifier
- opened_at
- closed_at
- qr validity
- status

### MenuCategory
- id
- location id
- name
- display order
- status

### MenuItem
- id
- category id
- name
- description
- status

### MenuItemLocation
- menu item id
- location id
- availability
- internal price
- effective dates

### KitchenStation
- id
- location id
- name
- status

### Order
- id
- order number
- location id
- customer type
- employee id
- guest session id
- order type
- scheduled_for
- status
- priority metadata
- timestamps

### OrderItem
- id
- order id
- menu item id
- kitchen station id
- ordered quantity
- unit price snapshot
- timestamps

### ConsumptionRecord
- id
- order item id
- served quantity
- validated_by
- served_at
- status

### LedgerAccount
- id
- owner type
- employee id / guest / official billing reference
- status

### LedgerEntry
- id
- ledger account id
- source type
- source id
- debit/credit amount
- reason
- reversal/reference id
- created_by
- created_at

### Review
- id
- location id
- employee id nullable
- anonymous flag
- review type
- rating/comment
- created_at

### ReviewCategory
- id
- location/global scope
- name
- enabled
- manager configurable flag

### Notification
- id
- recipient
- channel
- type
- status
- payload/reference
- sent_at
- created_at

### AuditLog
- id
- actor
- action
- entity type
- entity id
- old/new metadata
- timestamp

## Important constraints
- P-Number unique.
- Employee email unique where appropriate.
- Guest CNIC should be validated according to organizational policy.
- Order items must have positive ordered quantity.
- Served quantity cannot be negative and cannot exceed ordered quantity without
an explicit approved exception.
- Ledger entries cannot be deleted.
- Official guest entries must not post to employee personal ledger.
- Private guest entries must reference the responsible host employee.
