# Login and Employee Self-Registration

## Default credentials

A default system administrator is seeded automatically:

| Field | Value |
|-------|-------|
| **P-Number** | `ADMIN001` |
| **Password** | `Admin@12345` |
| Email | `admin@example.com` |
| Role | `SYSTEM_ADMINISTRATOR` |

Log in at `/login` with the P-Number and password. This admin approves
employee registrations and creates other employees.

**Change this password after first login** (use **Forgot password** on the
login page; the OTP goes to the backend log, see below).

Other fixed defaults (infrastructure, not app logins):

| What | Value |
|------|-------|
| Postgres (docker-compose) | user `mess` / password `mess` / database `mess` |
| Allowed registration email domain | `example.com` (setting `ALLOWED_EMAIL_DOMAINS`) |
| Web app (Docker) | http://localhost:8080 |
| Web app (local dev) | http://localhost:5173 |
| API | http://localhost:8000/api/v1 |

### How the admin is seeded

- **Docker:** `docker compose up` seeds it automatically on container
  start, right after migrations.
- **Local dev:** run it once from `backend/` with the virtualenv active:

  ```sh
  python -m app.scripts.seed_admin
  ```

The seed is safe to re-run: if `ADMIN001` already exists it is left
unchanged, so a changed password is never reset.

To use different values, pass flags or set env vars before the first seed:

```sh
python -m app.scripts.seed_admin --p-no HR001 --email hr@yourcompany.com --password 'Str0ng-pass'
```

| Flag | Env var |
|------|---------|
| `--p-no` | `SEED_ADMIN_P_NO` |
| `--email` | `SEED_ADMIN_EMAIL` |
| `--name` | `SEED_ADMIN_NAME` |
| `--password` | `SEED_ADMIN_PASSWORD` |

With `ENVIRONMENT=production`, the seed refuses to use the built-in default
password; set `SEED_ADMIN_PASSWORD` instead.

## Before employees register: allow your company email domain

Self-registration only accepts emails from domains listed in
`ALLOWED_EMAIL_DOMAINS` (comma-separated). The default is `example.com`.

- Local dev: set it in `backend/.env`, for example
  `ALLOWED_EMAIL_DOMAINS=yourcompany.com`.
- Docker: add `ALLOWED_EMAIL_DOMAINS: yourcompany.com` under the
  `backend.environment` section of `docker-compose.yml`, then run
  `docker compose up -d backend`.

## Emails (OTPs and temporary passwords)

No real email provider is wired up yet. Every email is written to the
backend log instead. To read OTP codes and temporary passwords:

```sh
docker compose logs -f backend     # look for lines containing "EMAIL to="
```

For local dev, check the terminal running `uvicorn`.

## How an employee registers themselves

### 1. The employee submits a registration

1. Open the web app and go to **Register** (`/register`).
2. Fill in:
   - **P-Number**: 3–20 characters, letters, digits or `-`.
   - **Full name**
   - **Company email**: must use an allowed domain (see above).
3. Submit. The registration is now **PENDING**. The employee cannot log in yet.

### 2. An administrator approves it

1. Log in as a `SYSTEM_ADMINISTRATOR` or `SYSTEM_MANAGER`.
2. Go to **Administration → Employees** (`/admin`) and find it under
   **Pending registrations**.
3. Click **Approve** (or **Reject**).

On approval, the system creates the employee account with a
**temporary password** and emails it to the employee (in dev, it appears in
the backend log as `Your P-Number is ... and temporary password is ...`).

### 3. The employee activates the account

1. Go to **Activate account** (`/activate`).
2. Enter the **P-Number** and the **temporary password**.
3. A 6-digit **OTP** is emailed (in dev, it's in the backend log). Enter it.
   It expires after 5 minutes, allows 5 attempts, and can be resent after 60 seconds.
4. Choose a **new password**: at least 8 characters, with at least one
   letter and one digit.
5. The employee is signed in. From now on they log in at `/login` with
   P-Number and their new password.

### Notes

- After 5 wrong passwords in a row, login is locked for 15 minutes.
- Forgotten password: `/forgot-password` → OTP by email → set a new password.
- Self-registered employees always get the `EMPLOYEE` role. There is
  currently no way to change an existing employee's role from the UI or API.
- To give someone another role (server, kitchen operator, location manager,
  etc.), an administrator creates the account directly with **Create
  employee** under **Administration → Employees** and picks the role there.
  Those employees skip registration and start at the activation step
  (step 3), using the temporary password emailed to them.
