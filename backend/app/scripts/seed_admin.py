"""Seed the default system administrator so a fresh install can be logged into.

    python -m app.scripts.seed_admin
    python -m app.scripts.seed_admin --p-no ADMIN001 --password 'S3cret-pass'

Defaults can also be set via env vars: SEED_ADMIN_P_NO, SEED_ADMIN_EMAIL,
SEED_ADMIN_NAME, SEED_ADMIN_PASSWORD.

Safe to re-run: if an employee with the P-Number already exists, nothing is
changed (an existing password is never overwritten). In production the
built-in default password is refused; pass an explicit one.
"""

import argparse
import asyncio
import os
import sys

import app.models  # noqa: F401  -- registers every model with the mapper
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, engine
from app.core.security import hash_password
from app.models.employee import Employee
from app.models.enums import EmployeeRole, EmployeeStatus, PasswordState
from app.repositories.employee_repository import EmployeeRepository
from app.services.audit_service import AuditService

DEFAULT_P_NO = "ADMIN001"
DEFAULT_EMAIL = "admin@example.com"
DEFAULT_NAME = "System Administrator"
DEFAULT_PASSWORD = "Admin@12345"


async def _run(*, p_no: str, email: str, name: str, password: str) -> int:
    if get_settings().is_production and password == DEFAULT_PASSWORD:
        print(
            "Refusing to seed the built-in default password in production; "
            "pass --password or set SEED_ADMIN_PASSWORD.",
            file=sys.stderr,
        )
        return 1

    async with AsyncSessionLocal() as session:
        employees = EmployeeRepository(session)
        if await employees.get_by_p_no(p_no) is not None:
            print(f"Admin {p_no} already exists -- left unchanged.")
        elif await employees.get_by_email(email) is not None:
            print(f"An employee with email {email} already exists.", file=sys.stderr)
            return 1
        else:
            admin = Employee(
                p_no=p_no,
                name=name,
                email=email,
                department=None,
                password_hash=hash_password(password),
                password_state=PasswordState.OK,
                status=EmployeeStatus.ACTIVE,
                role=EmployeeRole.SYSTEM_ADMINISTRATOR,
            )
            employees.add(admin)
            await employees.flush()
            await AuditService(session).record(
                action="employee.seeded_admin",
                entity_type="employee",
                entity_id=str(admin.id),
                new_values={"p_no": p_no, "email": email, "role": admin.role.value},
            )
            await session.commit()
            print(f"Seeded admin {p_no} ({email}).")

    await engine.dispose()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--p-no", default=os.getenv("SEED_ADMIN_P_NO", DEFAULT_P_NO))
    parser.add_argument("--email", default=os.getenv("SEED_ADMIN_EMAIL", DEFAULT_EMAIL))
    parser.add_argument("--name", default=os.getenv("SEED_ADMIN_NAME", DEFAULT_NAME))
    parser.add_argument("--password", default=os.getenv("SEED_ADMIN_PASSWORD", DEFAULT_PASSWORD))
    args = parser.parse_args()
    raise SystemExit(
        asyncio.run(_run(p_no=args.p_no, email=args.email, name=args.name, password=args.password))
    )


if __name__ == "__main__":
    main()
