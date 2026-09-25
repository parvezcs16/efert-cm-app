from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AccountLockedError, AuthenticationError, ValidationAppError
from app.core.security import verify_password
from app.models.employee import Employee
from app.models.enums import EmployeeStatus
from app.repositories.employee_repository import EmployeeRepository
from app.services.audit_service import AuditService
from app.services.auth.token_service import TokenPair, TokenService

settings = get_settings()

_GENERIC_INVALID_CREDENTIALS = "Invalid P-Number or password"


class LoginService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.employees = EmployeeRepository(db)
        self.tokens = TokenService(db)
        self.audit = AuditService(db)

    async def login(self, *, p_no: str, password: str) -> tuple[TokenPair, Employee]:
        employee = await self.employees.get_by_p_no(p_no)
        if employee is None:
            raise AuthenticationError(_GENERIC_INVALID_CREDENTIALS)

        if employee.locked_until is not None and employee.locked_until > datetime.now(UTC):
            raise AccountLockedError("Account is temporarily locked due to failed login attempts")

        if not verify_password(password, employee.password_hash):
            await self._register_failed_attempt(employee)
            raise AuthenticationError(_GENERIC_INVALID_CREDENTIALS)

        if employee.status == EmployeeStatus.PENDING_ACTIVATION:
            raise ValidationAppError("Account must be activated before logging in")
        if employee.status in (EmployeeStatus.SUSPENDED, EmployeeStatus.INACTIVE):
            raise AuthenticationError("Account is not active")

        employee.failed_login_attempts = 0
        employee.locked_until = None
        await self.employees.flush()

        pair = await self.tokens.issue_pair(employee)
        await self.audit.record(
            action="login.success", entity_type="employee", entity_id=str(employee.id)
        )
        return pair, employee

    async def _register_failed_attempt(self, employee: Employee) -> None:
        employee.failed_login_attempts += 1
        if employee.failed_login_attempts >= settings.login_max_attempts:
            employee.locked_until = datetime.now(UTC) + timedelta(
                minutes=settings.login_lockout_minutes
            )
            await self.audit.record(
                action="login.locked", entity_type="employee", entity_id=str(employee.id)
            )
        await self.employees.flush()
        await self.audit.record(
            action="login.failed", entity_type="employee", entity_id=str(employee.id)
        )
