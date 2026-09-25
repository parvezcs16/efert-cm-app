from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.billing import LedgerEntry
from app.models.employee import Employee
from app.models.enums import (
    EmployeeRole,
    EmployeeStatus,
    LedgerEntryType,
    LedgerSourceType,
    PasswordState,
    StatementFrequency,
)
from app.models.notification import Notification
from app.services.billing.ledger_service import LedgerService
from app.services.billing.statement_service import StatementService, schedule_next_statement
from tests.conftest import SeedEmployee, extract_otp


async def _make_active_employee(
    db: AsyncSession, *, p_no: str, email: str, frequency: StatementFrequency
) -> Employee:
    employee = Employee(
        p_no=p_no,
        name="Statement Tester",
        email=email,
        password_hash=hash_password("Passw0rd1"),
        password_state=PasswordState.OK,
        status=EmployeeStatus.ACTIVE,
        role=EmployeeRole.EMPLOYEE,
        statement_frequency=frequency,
    )
    db.add(employee)
    await db.flush()
    return employee


async def test_schedule_next_statement_advances_by_frequency(db_session: AsyncSession) -> None:
    employee = await _make_active_employee(
        db_session, p_no="STM-001", email="stm001@example.com", frequency=StatementFrequency.WEEKLY
    )
    base = datetime.now(UTC)
    schedule_next_statement(employee, from_time=base)
    assert employee.next_statement_due_at == base + timedelta(days=7)


async def test_send_due_statements_emails_and_creates_notification(
    db_session: AsyncSession,
) -> None:
    employee = await _make_active_employee(
        db_session, p_no="STM-002", email="stm002@example.com", frequency=StatementFrequency.DAILY
    )
    employee.next_statement_due_at = datetime.now(UTC) - timedelta(minutes=1)

    ledger = LedgerService(db_session)
    account = await ledger.get_or_create_employee_account(employee.id)

    db_session.add(
        LedgerEntry(
            ledger_account_id=account.id,
            source_type=LedgerSourceType.PERSONAL_CONSUMPTION,
            entry_type=LedgerEntryType.DEBIT,
            amount="42.00",
            reason="Test charge",
        )
    )
    await db_session.flush()

    count = await StatementService(db_session).send_due_statements()
    assert count == 1

    await db_session.refresh(employee)
    assert employee.next_statement_due_at > datetime.now(UTC)

    result = await db_session.execute(
        select(Notification).where(Notification.recipient == "stm002@example.com")
    )
    notifications = result.scalars().all()
    assert len(notifications) == 1
    assert notifications[0].type == "STATEMENT"
    assert notifications[0].status.value == "SENT"


async def test_employee_not_yet_due_is_not_sent(db_session: AsyncSession) -> None:
    employee = await _make_active_employee(
        db_session, p_no="STM-003", email="stm003@example.com", frequency=StatementFrequency.MONTHLY
    )
    employee.next_statement_due_at = datetime.now(UTC) + timedelta(days=10)
    await db_session.flush()

    count = await StatementService(db_session).send_due_statements()
    assert count == 0


async def test_activation_schedules_first_statement(
    client: AsyncClient, seed_active_employee: SeedEmployee, outbox: list[dict[str, str]]
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-090", email="admin90@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_login = await client.post(
        "/api/v1/auth/login", json={"p_no": admin.p_no, "password": admin_password}
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    register = await client.post(
        "/api/v1/auth/register",
        json={"p_no": "EMP-090", "email": "emp90@example.com", "name": "New Hire"},
    )
    registration_id = register.json()["id"]
    await client.post(
        f"/api/v1/auth/registrations/{registration_id}/approve", headers=admin_headers
    )

    approval_email = next(e for e in outbox if e["to"] == "emp90@example.com")
    temporary_password = approval_email["body"].split("temporary password is ")[1].split(".")[0]

    await client.post(
        "/api/v1/auth/activation/start",
        json={"p_no": "EMP-090", "temporary_password": temporary_password},
    )
    activation_email = next(e for e in outbox if e["subject"] == "Your activation code")
    code = extract_otp(activation_email["body"])
    verify = await client.post(
        "/api/v1/auth/activation/verify-otp", json={"p_no": "EMP-090", "code": code}
    )
    change_token = verify.json()["change_token"]

    profile = await client.post(
        "/api/v1/auth/activation/set-password",
        json={"p_no": "EMP-090", "change_token": change_token, "new_password": "NewPassw0rd1"},
    )
    access_token = profile.json()["access_token"]
    me = await client.get(
        "/api/v1/employees/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me.status_code == 200
    assert me.json()["statement_frequency"] == "MONTHLY"
    assert me.json()["next_statement_due_at"] is not None
