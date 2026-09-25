import secrets
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictError, ValidationAppError
from app.core.security import hash_password
from app.models.employee import Employee, EmployeeRegistration
from app.models.enums import EmployeeRole, EmployeeStatus, PasswordState, RegistrationStatus
from app.repositories.employee_repository import EmployeeRegistrationRepository, EmployeeRepository
from app.services.audit_service import AuditService

settings = get_settings()


def _generate_temporary_password() -> str:
    # Alphanumeric, always containing a digit so it passes the standard
    # password-strength check when the employee later sets a real one.
    return secrets.token_urlsafe(9) + str(secrets.randbelow(10))


class RegistrationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.employees = EmployeeRepository(db)
        self.registrations = EmployeeRegistrationRepository(db)
        self.audit = AuditService(db)

    def _assert_domain_allowed(self, email: str) -> None:
        domain = email.rsplit("@", 1)[-1].lower()
        if domain not in settings.allowed_email_domain_list:
            raise ValidationAppError(f"Email domain '{domain}' is not an allowed company domain")

    async def register(
        self, *, p_no: str, email: str, name: str, department: str | None
    ) -> EmployeeRegistration:
        self._assert_domain_allowed(email)

        if await self.employees.get_by_p_no(p_no) is not None:
            raise ConflictError("An employee with this P-Number already exists")
        if await self.registrations.get_pending_by_p_no(p_no) is not None:
            raise ConflictError("A pending registration already exists for this P-Number")

        registration = EmployeeRegistration(
            p_no=p_no, email=email, name=name, department=department
        )
        self.registrations.add(registration)
        await self.registrations.flush()

        await self.audit.record(
            action="registration.submitted",
            entity_type="employee_registration",
            entity_id=str(registration.id),
            new_values={"p_no": p_no, "email": email},
        )
        return registration

    async def approve(
        self, *, registration_id: uuid.UUID, decided_by_id: uuid.UUID
    ) -> tuple[Employee, str]:
        registration = await self.registrations.get_by_id(registration_id)
        if registration is None:
            raise ValidationAppError("Registration not found")
        if registration.status != RegistrationStatus.PENDING:
            raise ConflictError("Registration has already been decided")

        temporary_password = _generate_temporary_password()
        employee = Employee(
            p_no=registration.p_no,
            name=registration.name,
            email=registration.email,
            department=registration.department,
            password_hash=hash_password(temporary_password),
            password_state=PasswordState.MUST_CHANGE,
            status=EmployeeStatus.PENDING_ACTIVATION,
            role=EmployeeRole.EMPLOYEE,
        )
        self.employees.add(employee)
        await self.employees.flush()

        registration.status = RegistrationStatus.APPROVED
        registration.employee_id = employee.id
        registration.decided_by_id = decided_by_id
        await self.registrations.flush()

        await self.audit.record(
            action="registration.approved",
            entity_type="employee_registration",
            entity_id=str(registration.id),
            actor_employee_id=decided_by_id,
            new_values={"employee_id": str(employee.id)},
        )
        return employee, temporary_password

    async def reject(
        self, *, registration_id: uuid.UUID, decided_by_id: uuid.UUID, reason: str | None
    ) -> EmployeeRegistration:
        registration = await self.registrations.get_by_id(registration_id)
        if registration is None:
            raise ValidationAppError("Registration not found")
        if registration.status != RegistrationStatus.PENDING:
            raise ConflictError("Registration has already been decided")

        registration.status = RegistrationStatus.REJECTED
        registration.decided_by_id = decided_by_id
        registration.decision_reason = reason
        await self.registrations.flush()

        await self.audit.record(
            action="registration.rejected",
            entity_type="employee_registration",
            entity_id=str(registration.id),
            actor_employee_id=decided_by_id,
            new_values={"reason": reason},
        )
        return registration
