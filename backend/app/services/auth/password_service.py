from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationAppError
from app.core.security import create_purpose_token, decode_purpose_token, hash_password
from app.models.enums import EmployeeStatus, OtpPurpose
from app.repositories.employee_repository import EmployeeRepository
from app.services.audit_service import AuditService
from app.services.auth.otp_service import OtpService
from app.services.notifications.dispatch_service import NotificationDispatchService

PURPOSE = "PASSWORD_RESET"


class PasswordService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.employees = EmployeeRepository(db)
        self.otp = OtpService(db)
        self.audit = AuditService(db)
        self.notifier = NotificationDispatchService(db)

    async def forgot(self, *, p_no: str) -> None:
        """Always succeeds from the caller's perspective, even if the
        P-Number is unknown, so the endpoint cannot be used to enumerate
        valid accounts."""
        employee = await self.employees.get_by_p_no(p_no)
        if employee is None or employee.status != EmployeeStatus.ACTIVE:
            return

        code = await self.otp.issue(
            subject=p_no, purpose=OtpPurpose.PASSWORD_RESET, employee_id=employee.id
        )
        await self.notifier.send_email(
            to=employee.email,
            subject="Your password reset code",
            body=f"Your password reset code is {code}. It expires shortly.",
            type="PASSWORD_RESET_OTP",
            payload_reference=str(employee.id),
        )

    async def verify_reset_otp(self, *, p_no: str, code: str) -> str:
        await self.otp.verify(subject=p_no, purpose=OtpPurpose.PASSWORD_RESET, code=code)
        return create_purpose_token(subject=p_no, purpose=PURPOSE)

    async def reset(self, *, p_no: str, change_token: str, new_password: str) -> None:
        try:
            decode_purpose_token(change_token, purpose=PURPOSE, subject=p_no)
        except ValueError as exc:
            raise ValidationAppError(str(exc)) from exc

        employee = await self.employees.get_by_p_no(p_no)
        if employee is None:
            raise ValidationAppError("Invalid request")

        employee.password_hash = hash_password(new_password)
        await self.employees.flush()

        await self.audit.record(
            action="password.reset", entity_type="employee", entity_id=str(employee.id)
        )
