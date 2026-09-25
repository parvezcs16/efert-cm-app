import secrets
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.employee import Employee
from app.models.enums import EmployeeRole, EmployeeStatus, PasswordState, StatementFrequency
from app.repositories.employee_repository import EmployeeRepository
from app.services.audit_service import AuditService
from app.services.billing.statement_service import schedule_next_statement


def _generate_temporary_password() -> str:
    return secrets.token_urlsafe(9) + str(secrets.randbelow(10))


class EmployeeService:
    """Employee directory management. Registration/activation/login live in
    the auth module; this covers admin-side employee record management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.employees = EmployeeRepository(db)
        self.audit = AuditService(db)

    async def create_by_admin(
        self,
        *,
        p_no: str,
        name: str,
        email: str,
        department: str | None,
        role: EmployeeRole,
        created_by_id: uuid.UUID,
    ) -> tuple[Employee, str]:
        if await self.employees.get_by_p_no(p_no) is not None:
            raise ConflictError("An employee with this P-Number already exists")
        if await self.employees.get_by_email(email) is not None:
            raise ConflictError("An employee with this email already exists")

        temporary_password = _generate_temporary_password()
        employee = Employee(
            p_no=p_no,
            name=name,
            email=email,
            department=department,
            password_hash=hash_password(temporary_password),
            password_state=PasswordState.MUST_CHANGE,
            status=EmployeeStatus.PENDING_ACTIVATION,
            role=role,
        )
        self.employees.add(employee)
        await self.employees.flush()

        await self.audit.record(
            action="employee.created_by_admin",
            entity_type="employee",
            entity_id=str(employee.id),
            actor_employee_id=created_by_id,
            new_values={"p_no": p_no, "role": role.value},
        )
        return employee, temporary_password

    async def get(self, employee_id: uuid.UUID) -> Employee:
        employee = await self.employees.get_by_id(employee_id)
        if employee is None:
            raise NotFoundError("Employee not found")
        return employee

    async def search(
        self, *, q: str | None = None, roles: list[EmployeeRole] | None = None
    ) -> list[Employee]:
        return await self.employees.search(q=q, roles=roles)

    async def update_statement_frequency(
        self, employee_id: uuid.UUID, frequency: StatementFrequency
    ) -> Employee:
        employee = await self.get(employee_id)
        employee.statement_frequency = frequency
        if employee.next_statement_due_at is not None:
            schedule_next_statement(employee)
        await self.employees.flush()

        await self.audit.record(
            action="employee.statement_frequency_updated",
            entity_type="employee",
            entity_id=str(employee.id),
            actor_employee_id=employee_id,
            new_values={"statement_frequency": frequency.value},
        )
        return employee
