from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationAppError
from app.core.security import (
    create_purpose_token,
    decode_purpose_token,
    hash_password,
    verify_password,
)
from app.models.employee import Employee
from app.models.enums import EmployeeStatus, OtpPurpose, PasswordState
from app.repositories.employee_repository import EmployeeRepository
from app.services.audit_service import AuditService
from app.services.auth.otp_service import OtpService
from app.services.billing.statement_service import schedule_next_statement
from app.services.notifications.dispatch_service import NotificationDispatchService

PURPOSE = "ACTIVATION"


class ActivationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.employees = EmployeeRepository(db)
        self.otp = OtpService(db)
        self.audit = AuditService(db)
        self.notifier = NotificationDispatchService(db)

    async def _get_activatable_employee(self, p_no: str) -> Employee:
        employee = await self.employees.get_by_p_no(p_no)
        if employee is None:
            raise ValidationAppError("Invalid P-Number or temporary password")
        if employee.status != EmployeeStatus.PENDING_ACTIVATION:
            raise ValidationAppError("This account is not pending activation")
        return employee

    async def start(self, *, p_no: str, temporary_password: str) -> None:
        employee = await self._get_activatable_employee(p_no)
        if not verify_password(temporary_password, employee.password_hash):
            await self.audit.record(
                action="activation.invalid_credentials",
                entity_type="employee",
                entity_id=str(employee.id),
            )
            raise ValidationAppError("Invalid P-Number or temporary password")

        code = await self.otp.issue(
            subject=p_no, purpose=OtpPurpose.ACTIVATION, employee_id=employee.id
        )
        await self.notifier.send_email(
            to=employee.email,
            subject="Your activation code",
            body=f"Your activation code is {code}. It expires shortly.",
            type="ACTIVATION_OTP",
            payload_reference=str(employee.id),
        )

    async def verify_otp(self, *, p_no: str, code: str) -> str:
        await self._get_activatable_employee(p_no)
        await self.otp.verify(subject=p_no, purpose=OtpPurpose.ACTIVATION, code=code)
        return create_purpose_token(subject=p_no, purpose=PURPOSE)

    async def set_password(self, *, p_no: str, change_token: str, new_password: str) -> Employee:
        try:
            decode_purpose_token(change_token, purpose=PURPOSE, subject=p_no)
        except ValueError as exc:
            raise ValidationAppError(str(exc)) from exc

        employee = await self._get_activatable_employee(p_no)
        employee.password_hash = hash_password(new_password)
        employee.password_state = PasswordState.OK
        employee.status = EmployeeStatus.ACTIVE
        schedule_next_statement(employee)
        await self.employees.flush()

        await self.audit.record(
            action="employee.activated",
            entity_type="employee",
            entity_id=str(employee.id),
        )
        return employee
