# Guest Management

## Registration
Required:
- Guest name
- Company name
- CNIC
- Guest type
- Host employee
- Accompanying person count

## Session
A host can create a guest session and generate a QR.

The same guest may have multiple sessions over time.

The guest may place multiple orders while the session is active.

## Billing
PRIVATE:
- Host employee is responsible.
- Entries are included in private guest reporting.

OFFICIAL:
- Separate official billing.
- No employee deduction.

## QR
Use a signed, non-guessable temporary token.
Do not encode sensitive guest data directly into the QR.
The QR should identify a server-side guest session.

Closing a session prevents normal continued ordering according to the configured
session state, while the 24-hour QR invalidation rule is handled separately.
