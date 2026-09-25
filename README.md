# Central Mess Management System

Multi-location central mess platform: employee/guest ordering, kitchen
operations, consumption tracking, mess ledgers, official guest billing,
notifications, reviews, and administration. See [docs/](docs/) for the full
functional and technical specification, and [AGENTS.md](AGENTS.md) /
[CLAUDE.md](CLAUDE.md) for development conventions.

## Stack

- Backend: Python 3.12, FastAPI, SQLAlchemy 2.x (async), Alembic, PostgreSQL
- Frontend: React + TypeScript + Vite, Tailwind CSS + shadcn/ui
- Mobile: Flutter (Dart), native Android/iOS
- Deployment: Docker + Nginx

## Project layout

```
backend/   FastAPI app (app/core, models, schemas, repositories, services, api/v1, websocket, workers)
frontend/  React app (src/features/<domain>, src/components, src/lib)
mobile/    Flutter app (lib/core, lib/features/<domain>, lib/widgets)
docs/      Functional and technical specification
```

## Local development

### Backend

```
cd backend
python -m venv .venv
.venv/Scripts/activate        # .venv\Scripts\Activate.ps1 on PowerShell
pip install -r requirements-dev.txt
cp .env.example .env          # adjust DATABASE_URL etc. as needed
uvicorn app.main:app --reload
```

Runs at http://localhost:8000. Health checks: `GET /api/v1/health`,
`GET /api/v1/health/db`.

Tests: `pytest` (requires a reachable Postgres; tests create/drop their own
schema in a separate database, `mess_test` by default -- override with
`TEST_DATABASE_URL`). Lint: `ruff check .`. Types: `mypy app`.

Migrations (once a Postgres instance is reachable via `DATABASE_URL`):

```
alembic revision --autogenerate -m "message"
alembic upgrade head
```

### Frontend

```
cd frontend
npm install
npm run dev
```

Runs at http://localhost:5173 and proxies `/api/*` to the backend on port
8000 (see `vite.config.ts`).

Build: `npm run build`. Lint: `npm run lint`.

### Mobile

```
cd mobile
flutter pub get
flutter run -d chrome \
  --dart-define=API_BASE_URL=http://localhost:8000/api/v1 \
  --dart-define=WEB_APP_BASE_URL=http://localhost:8000
```

Swap `-d chrome` for `-d windows`/`-d <device-id>` and adjust
`API_BASE_URL` for an Android emulator (`http://10.0.2.2:8000/api/v1`) or a
physical device (your machine's LAN IP). `WEB_APP_BASE_URL` is only used to
build the guest QR link (see "Guest self-service" below) -- point it at
wherever the web frontend is actually deployed.

Analyze: `flutter analyze`. Tests: `flutter test`. Release build:
`flutter build apk` (Android) or `flutter build ios` (macOS + Xcode only,
not buildable from this checkout on Windows).

**Guest self-service is intentionally web-only.** The native app is for
employees/servers/kitchen/managers; a host still registers guests and opens
QR sessions from the app, but the QR itself opens the existing React guest
portal (`/guest?token=...`) in the guest's own browser rather than requiring
a guest to install anything. See docs/implementation-notes.md "Mobile app"
for the full rationale.

### Full stack via Docker

```
docker compose up --build
```

Starts Postgres, the backend (migrations run automatically on container
start, then serves on :8000), and the frontend behind Nginx on :8080, which
proxies `/api/*` and `/ws/*` to the backend.

## Status

- **Phase 1 (foundation)**: project scaffolding, configuration, logging,
  error handling, database/session wiring, migrations setup, Docker.
- **Phase 2 (authentication)**: employee model, self-registration +
  admin-approval workflow, admin-created employees, OTP-gated activation
  (temporary password -> OTP -> mandatory password change), login with
  lockout, JWT access + rotating refresh tokens, OTP-gated password reset,
  RBAC (`require_roles`), audit logging, a minimal notification port (email
  only, console-logged for now).
- **Phase 3 (locations and menu)**: locations with an eligible-role-checked
  manager assignment, kitchen stations, location-scoped menu categories,
  menu items, and per-location availability/pricing (`MenuItemLocation`).
  RBAC scoped so a `LOCATION_MANAGER` can only manage their own assigned
  location (`require_location_authority`); system-level roles can manage
  any location.
- **Phase 4 (employee ordering)**: price-free menu browsing, DINE_IN /
  TAKEAWAY / BOOK_FOR_LATER order creation with server-side price
  snapshotting (`OrderItem.unit_price`), order history scoped to the
  requesting employee, and cancellation before serving.
- **Phase 5 (kitchen)**: order status lifecycle
  (PENDING -> CONFIRMED -> QUEUED -> PREPARING -> READY -> SERVED) driven
  by kitchen/server staff, per-item kitchen station routing at queue time,
  a station-queue view sorted by priority (immediate orders before booked,
  FIFO within each), a server "serve directly" override that bypasses the
  intermediate steps, and realtime kitchen-display updates over WebSocket
  (`/ws/kitchen/{location_id}?token=...`).
- **Phase 6 (guests)**: guest registration and repeatable QR-token guest
  sessions (opened/closed/reopened by a host employee), a separate
  short-lived guest access token (`/guest/auth`) for independent
  QR-authenticated guest ordering, and PRIVATE/OFFICIAL guest-type
  tracking for Phase 8 billing to key off of. `Order` now supports both
  employee and guest customers with a DB CHECK constraint enforcing
  exactly one is set.
- **Phase 7 (booked order management)**: ingredient confirmation gating for
  BOOK_FOR_LATER orders (blocks the normal kitchen PENDING -> CONFIRMED
  transition until reviewed), a manager delay response that updates the
  serving time and notifies the customer, and a realtime "booking.alert"
  broadcast over the same kitchen WebSocket channel the moment a booked
  order is placed.
- **Phase 8 (consumption and billing)**: serving an order posts a
  validated `ConsumptionRecord` per item and an immutable ledger charge to
  the correct account (employee personal / host's account for a PRIVATE
  guest / a location's OFFICIAL account for an OFFICIAL guest); an
  employee-initiated served-quantity correction, gated by server
  validation, posts a single net adjustment entry referencing the original
  charge rather than editing it; personal / private-guest / official /
  consolidated statement views computed directly from ledger entries; an
  employee's statement-frequency preference.
- **Phase 9 (reviews and notifications)**: overall and per-order reviews
  with anonymity masking and system-defined + manager-defined per-location
  categories (the four defaults are seeded automatically); every
  notification email now persists a `Notification` record via
  `NotificationDispatchService`; an in-process scheduler periodically
  emails each employee's due statement based on their frequency
  preference.
- **Phase 10 (reporting and hardening)**: per-location sales-summary and
  reconciliation reports, a filterable audit-log query endpoint, manual
  billing adjustments (`Adjust/reverse billing`, the one Phase 8 gap),
  plus concrete security hardening (production startup guard against the
  default secret key, non-root backend Docker image, nginx security
  headers + per-IP auth rate limiting). Backup/recovery, production
  deployment, and performance guidance are documented in
  [docs/operations.md](docs/operations.md) rather than built as code,
  since they're operational concerns without a real deployment target in
  this checkout.

- **Web frontend**: a React + TypeScript + Vite app covering every backend
  feature area (auth/activation, employee ordering, kitchen display with
  live WebSocket updates, guest hosting + guest QR self-service portal,
  billing/statements, reviews, and admin: employees/locations/menu/reports)
  with role-based routing and navigation.
- **Mobile app**: a native Flutter app (Android/iOS/web/desktop from one
  codebase) covering the same feature set as the web frontend for
  employees/servers/kitchen staff/managers -- auth + activation, ordering,
  order history/detail with correction requests, kitchen queue with live
  WebSocket updates, guest hosting (register/session/QR -- the guest
  themselves still uses the web portal, see "Mobile" above), billing
  statements with frequency preference, reviews, and the full
  administration area (employees/locations/menu/reports). Secure token
  storage via the platform keystore; `go_router` + a role-filtered
  navigation drawer.

**All 10 backend phases of docs/implementation-plan.md are implemented and
covered by tests** (65 backend tests, all passing against a real
Postgres instance). See
[docs/implementation-plan.md](docs/implementation-plan.md) for the
phased build order, [docs/implementation-notes.md](docs/implementation-notes.md)
for assumptions made where requirements were ambiguous, and
[docs/operations.md](docs/operations.md) for deployment/ops guidance.
