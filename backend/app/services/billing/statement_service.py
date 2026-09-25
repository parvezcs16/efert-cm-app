from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.employee import Employee
from app.models.enums import LedgerSourceType, StatementFrequency
from app.repositories.employee_repository import EmployeeRepository
from app.services.billing.ledger_service import LedgerService
from app.services.notifications.dispatch_service import NotificationDispatchService

logger = get_logger("billing.statements")

# MONTHLY is a fixed 30-day window here, not a calendar month -- simpler,
# and the docs don't specify calendar-month semantics.
_FREQUENCY_INTERVAL = {
    StatementFrequency.DAILY: timedelta(days=1),
    StatementFrequency.WEEKLY: timedelta(days=7),
    StatementFrequency.BIWEEKLY: timedelta(days=14),
    StatementFrequency.MONTHLY: timedelta(days=30),
}


def schedule_next_statement(employee: Employee, *, from_time: datetime | None = None) -> None:
    """Sets/resets when this employee is next due a statement email, based
    on their current frequency preference. Called on activation and
    whenever the preference changes."""
    base = from_time or datetime.now(UTC)
    employee.next_statement_due_at = base + _FREQUENCY_INTERVAL[employee.statement_frequency]


class StatementService:
    """Generates and emails an employee's personal + private-guest
    statement from ledger transactions (docs/billing.md: "Statement
    generation should be based on ledger transactions, not mutable order
    state"), and advances each employee's next due date. Invoked
    periodically by app/workers/statement_scheduler.py."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.employees = EmployeeRepository(db)
        self.ledger = LedgerService(db)
        self.notifier = NotificationDispatchService(db)

    async def send_due_statements(self) -> int:
        now = datetime.now(UTC)
        due = await self.employees.list_due_for_statement(now)
        for employee in due:
            await self._send_one(employee, now)
        return len(due)

    async def _send_one(self, employee: Employee, now: datetime) -> None:
        assert employee.next_statement_due_at is not None
        since = employee.next_statement_due_at - _FREQUENCY_INTERVAL[employee.statement_frequency]

        account = await self.ledger.get_or_create_employee_account(employee.id)
        entries = await self.ledger.statement(
            account.id,
            source_types=[LedgerSourceType.PERSONAL_CONSUMPTION, LedgerSourceType.PRIVATE_GUEST],
            since=since,
            until=now,
        )

        lines = [
            f"- {e.created_at:%Y-%m-%d} {e.entry_type.value} {e.amount} ({e.reason})"
            for e in entries
        ]
        body = (
            f"Your {employee.statement_frequency.value.lower()} mess statement "
            f"({since:%Y-%m-%d} to {now:%Y-%m-%d}):\n\n"
            + ("\n".join(lines) if lines else "No activity in this period.")
        )
        await self.notifier.send_email(
            to=employee.email,
            subject="Your mess statement",
            body=body,
            type="STATEMENT",
            payload_reference=str(employee.id),
        )

        schedule_next_statement(employee, from_time=now)
        await self.employees.flush()
        logger.info("Sent statement to %s (%s)", employee.p_no, employee.statement_frequency.value)
