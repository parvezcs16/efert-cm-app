# Development Instructions

## Before coding
1. Read CLAUDE.md.
2. Read the relevant document in docs/.
3. Inspect existing models, services, routes, and tests.
4. Reuse existing abstractions before creating new ones.

## Architecture
Use a modular monolith.

Recommended backend modules:
- auth
- employees
- locations
- menu
- guests
- ordering
- kitchen
- consumption
- billing
- notifications
- reviews
- administration
- audit

Recommended layering:
API -> Service -> Repository -> Database

Keep business rules in services/domain logic, not route handlers.

## Database
- PostgreSQL.
- SQLAlchemy 2.x.
- Alembic migrations.
- Timezone-aware timestamps.
- Foreign keys and check constraints where useful.
- Financial records are append-only.
- Use transactions for state changes affecting consumption and billing.

## Security
- Hash passwords with a modern password hashing algorithm.
- Never store plaintext passwords or OTPs.
- Rate-limit authentication and OTP endpoints.
- Validate allowed email domains server-side.
- Enforce authorization server-side.
- Audit privileged changes.

## API
- Version APIs under /api/v1.
- Use Pydantic request/response schemas.
- Never expose ORM objects directly.
- Return consistent errors.
- Use idempotency where duplicate submissions are possible.

## Frontend
Organize by feature:
- auth
- ordering
- guests
- kitchen
- billing
- reviews
- administration

Do not duplicate authoritative business rules in React.

## Testing
At minimum test:
- employee activation
- OTP expiry/attempt limits
- password reset
- private guest billing
- official guest billing
- guest QR/session lifecycle
- order lifecycle
- scheduled orders
- kitchen priority
- ingredient confirmation
- served quantity
- quantity correction/validation
- cancellation
- ledger adjustments
- review anonymity
- location-specific menus/prices

## Change discipline
Do not change a business rule because it seems simpler.
If a requirement is ambiguous, document the assumption in the implementation
notes and keep the change isolated.
