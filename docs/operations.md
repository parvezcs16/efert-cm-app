# Operations

Phase 10 ("Reporting and Hardening") splits into application code -- built
and tested like every other phase (see docs/implementation-notes.md) -- and
genuinely operational concerns that don't take the form of application code
at all. This document covers the latter: backup/recovery, production
deployment, performance, and a summary of the security hardening already
in place versus what's deliberately left to infrastructure.

## What's application code (see implementation-notes.md Phase 10)

- Management reports: `GET /api/v1/reports/locations/{id}/sales-summary`
- Reconciliation: `GET /api/v1/reports/locations/{id}/reconciliation`
  (flags any served item whose billed amount doesn't match
  `served_quantity * unit_price` -- should never happen in normal
  operation; a mismatch indicates a bug or direct DB tampering)
- Audit log query: `GET /api/v1/reports/audit-log`
- Manual billing adjustments (the "Adjust/reverse billing" management
  capability that Phase 8 didn't cover):
  `POST /api/v1/billing/employees/{id}/adjustments`,
  `POST /api/v1/billing/official/{location_id}/adjustments`

## Security hardening

**Already in place, built across earlier phases:**
- Argon2 password hashing; OTP codes are never stored in plaintext, only
  an HMAC-SHA256 hash keyed with `SECRET_KEY`.
- JWT decode always pins `algorithms=["HS256"]` explicitly (prevents an
  algorithm-confusion/"none" attack).
- OTP resend cooldown + max-attempt lockout; login lockout after repeated
  failures (see Phase 2 notes for exact thresholds).
- `/auth/forgot-password` and login give identical responses whether or
  not the account exists (no enumeration via those two paths). Note:
  self-registration (`POST /auth/register`) *does* reveal whether a
  P-Number/email is already taken -- a deliberate, common trade-off for a
  registration flow, not an oversight.
- Every state-changing service call writes an AuditLog entry.
- Ownership checks return 404 (not 403) for another user's resource,
  avoiding resource-existence leaks.
- All DB access goes through SQLAlchemy's parameterized queries -- no
  raw string interpolation of user input anywhere in the codebase.
- Pydantic schemas define the exact accepted fields per endpoint; nothing
  is ever hydrated onto an ORM model directly from a raw request body
  (no mass-assignment surface).
- Dependencies are pinned to exact versions in requirements.txt.
- The app now refuses to start (`RuntimeError` at import time) if
  `ENVIRONMENT=production` and `SECRET_KEY` is still the placeholder
  default -- see `app/main.py:create_app`.
- Backend Docker image runs as a non-root user (`appuser`), not root.
- `frontend/nginx.conf` sets `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, and rate-limits `/api/v1/auth/*` per-IP
  (`limit_req_zone`) as defense in depth alongside the app-level OTP/login
  throttling.

**Deliberately left to infrastructure/deployment, not application code:**
- **TLS termination and HSTS.** `frontend/nginx.conf` is HTTP-only by
  design in this repo (no cert material to manage in a dev/CI checkout).
  A production deployment needs TLS in front of it (either nginx itself
  with real certs, or a load balancer/ingress terminating TLS) --
  `Strict-Transport-Security` should be added there, not before TLS
  exists, or it can lock out an HTTP-only preview environment.
- **WAF / broader rate limiting / DDoS protection** -- typically a
  reverse-proxy or cloud-provider concern, not something to bolt onto the
  application.
- **Dependency vulnerability scanning** (e.g. `pip-audit`, Dependabot,
  `npm audit` in CI) -- recommended, not run as part of this checkout.
- **Secrets management** -- `.env` files are fine for local dev; a real
  deployment should pull `SECRET_KEY`, `DATABASE_URL`, etc. from a secrets
  manager (not baked into the image or committed anywhere).

## Performance

No load-testing tool was run against this app as part of this checkout --
there's no realistic target environment in a local dev sandbox to point
one at, and premature load-test tuning without a real deployment profile
tends to optimize the wrong thing. What *is* in place:

- Every foreign key that's queried on (ownership checks, list-by-parent
  queries) has an index -- see each model file's `index=True` columns and
  the explicit composite index on `audit_logs`.
- `order_number` generation uses a Postgres `SEQUENCE` (`nextval`), not a
  read-then-increment pattern, so it's contention-free under concurrent
  order creation.
- Report/reconciliation queries batch their lookups (e.g.
  `ConsumptionRecordRepository.list_by_order_items`,
  `LedgerEntryRepository.net_amount_by_source_id`) rather than querying
  per row, but are not further optimized (no caching, no materialized
  views) -- fine at the data volumes a single mess/location realistically
  produces; revisit if a location's report queries are ever run over
  a full year of data rather than a rolling window.
- `MenuService.browse` is the one intentionally N+1-shaped query (documented
  in its docstring) on the assumption that a location's catalog is small
  (a handful of categories/items) -- revisit if that assumption stops
  holding.

Before a real production rollout, run a load test (k6, Locust, or similar)
against the actual deployment target, focused on the hottest paths:
`POST /orders`, kitchen status transitions, and the kitchen WebSocket
broadcast fan-out.

## Backup and recovery

The stack is a single PostgreSQL database (`docker-compose.yml`'s `db`
service, a named volume `db_data`). No backup automation is included in
this repo -- that belongs to wherever this is actually deployed (managed
Postgres services provide this natively; a self-managed instance needs a
cron-driven `pg_dump`/WAL-archiving job). Practical guidance:

- **Logical backup**: `pg_dump --format=custom` on a schedule, retained
  off-host (not just on the same volume/host as the live database).
- **Point-in-time recovery**: if RPO tighter than "since last dump"
  matters, enable WAL archiving (`archive_mode`) and use `pg_basebackup` +
  WAL replay rather than relying on `pg_dump` alone.
- **Restore drill**: periodically actually restore a backup into a
  throwaway database and run the app's Alembic `alembic upgrade head`
  against it (migrations must remain compatible with restored data) --
  an untested backup is not a backup.
- **What's append-only vs. what to focus recovery correctness on**:
  `ledger_entries` and `audit_logs` are never updated/deleted by any
  service code (see Phase 8/CLAUDE.md's immutability rule) -- a partial
  restore that's missing recent rows there is a correctness incident
  (lost financial history), more so than e.g. losing a few minutes of
  `notifications` rows.

## Production deployment

`docker-compose.yml` (root) is written for local/single-host use, not
turnkey production. Before deploying it as-is to production:

- Set real values for every secret in `backend/.env.example`
  (`SECRET_KEY` above all -- the app now refuses to start without one),
  and stop mounting `.env` files directly; use your platform's secret
  store.
- Put TLS in front of the `web` (nginx) service (see "Security hardening"
  above).
- Point `DATABASE_URL` at a managed/backed-up Postgres instance rather
  than the `db` service's local volume, or make sure that volume itself
  is backed up per the section above.
- `backend/docker-entrypoint.sh` runs `alembic upgrade head` on every
  container start -- fine for a single-instance deployment; for a
  multi-instance rollout, run migrations as a separate release step
  before scaling up new instances, so two instances never race to apply
  the same migration.
- The kitchen WebSocket manager (`app/websocket/manager.py`) and the
  statement scheduler (`app/workers/statement_scheduler.py`) both hold
  their state in-process and assume a single backend worker/process (see
  their docstrings and the Phase 5/9 implementation notes). Running
  multiple backend replicas without addressing this means: a kitchen
  display connected to replica A won't see a status change made via
  replica B, and due statements could in principle be double-sent if two
  replicas' scheduler loops both pick up the same employee in the same
  window (unlikely at low replica counts and an hourly check interval,
  but not structurally prevented). Both would need a shared
  broker/lock (e.g. Redis pub/sub, a `SELECT ... FOR UPDATE SKIP LOCKED`
  claim pattern) to run correctly behind more than one backend process.
- Health checks: `GET /api/v1/health` (liveness, no DB) and
  `GET /api/v1/health/db` (readiness, checks DB connectivity) already
  exist -- wire them into your platform's health-check config.
