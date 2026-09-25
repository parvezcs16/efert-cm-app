import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_employee, require_roles
from app.core.database import get_db
from app.models.employee import Employee
from app.models.enums import EmployeeRole
from app.schemas.auth import (
    ActivationStartRequest,
    ChangeTokenResponse,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MeResponse,
    MessageResponse,
    OtpVerifyRequest,
    RefreshRequest,
    RegistrationDecisionRequest,
    RegistrationRead,
    RegistrationRequest,
    SetPasswordRequest,
    TokenResponse,
)
from app.services.auth.activation_service import ActivationService
from app.services.auth.login_service import LoginService
from app.services.auth.password_service import PasswordService
from app.services.auth.registration_service import RegistrationService
from app.services.auth.token_service import TokenPair, TokenService
from app.services.notifications.dispatch_service import NotificationDispatchService

router = APIRouter(prefix="/auth", tags=["auth"])

REGISTRATION_REVIEWER_ROLES = (EmployeeRole.SYSTEM_MANAGER, EmployeeRole.SYSTEM_ADMINISTRATOR)


def _token_response(pair: TokenPair, *, must_change_password: bool) -> TokenResponse:
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
        must_change_password=must_change_password,
    )


@router.post("/register", response_model=RegistrationRead, status_code=201)
async def register(
    payload: RegistrationRequest, db: AsyncSession = Depends(get_db)
) -> RegistrationRead:
    registration = await RegistrationService(db).register(
        p_no=payload.p_no, email=payload.email, name=payload.name, department=payload.department
    )
    return RegistrationRead.model_validate(registration)


@router.get(
    "/registrations",
    response_model=list[RegistrationRead],
    dependencies=[Depends(require_roles(*REGISTRATION_REVIEWER_ROLES))],
)
async def list_pending_registrations(db: AsyncSession = Depends(get_db)) -> list[RegistrationRead]:
    registrations = await RegistrationService(db).registrations.list_pending()
    return [RegistrationRead.model_validate(r) for r in registrations]


@router.post("/registrations/{registration_id}/approve", response_model=MessageResponse)
async def approve_registration(
    registration_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    reviewer: Employee = Depends(require_roles(*REGISTRATION_REVIEWER_ROLES)),
) -> MessageResponse:
    service = RegistrationService(db)
    employee, temporary_password = await service.approve(
        registration_id=registration_id, decided_by_id=reviewer.id
    )
    await NotificationDispatchService(db).send_email(
        to=employee.email,
        subject="Your mess account has been approved",
        body=(
            f"Your P-Number is {employee.p_no} and temporary password is "
            f"{temporary_password}. Use it to activate your account."
        ),
        type="REGISTRATION_APPROVED",
        payload_reference=str(employee.id),
    )
    return MessageResponse(message="Registration approved")


@router.post("/registrations/{registration_id}/reject", response_model=MessageResponse)
async def reject_registration(
    registration_id: uuid.UUID,
    payload: RegistrationDecisionRequest,
    db: AsyncSession = Depends(get_db),
    reviewer: Employee = Depends(require_roles(*REGISTRATION_REVIEWER_ROLES)),
) -> MessageResponse:
    await RegistrationService(db).reject(
        registration_id=registration_id, decided_by_id=reviewer.id, reason=payload.reason
    )
    return MessageResponse(message="Registration rejected")


@router.post("/activation/start", response_model=MessageResponse)
async def activation_start(
    payload: ActivationStartRequest, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    await ActivationService(db).start(
        p_no=payload.p_no, temporary_password=payload.temporary_password
    )
    return MessageResponse(message="Activation code sent")


@router.post("/activation/verify-otp", response_model=ChangeTokenResponse)
async def activation_verify_otp(
    payload: OtpVerifyRequest, db: AsyncSession = Depends(get_db)
) -> ChangeTokenResponse:
    token = await ActivationService(db).verify_otp(p_no=payload.p_no, code=payload.code)
    return ChangeTokenResponse(change_token=token, expires_in=300)


@router.post("/activation/set-password", response_model=TokenResponse)
async def activation_set_password(
    payload: SetPasswordRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    employee = await ActivationService(db).set_password(
        p_no=payload.p_no, change_token=payload.change_token, new_password=payload.new_password
    )
    pair = await TokenService(db).issue_pair(employee)
    return _token_response(pair, must_change_password=False)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    pair, employee = await LoginService(db).login(p_no=payload.p_no, password=payload.password)
    return _token_response(pair, must_change_password=employee.password_state.value != "OK")


@router.post("/token/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    pair = await TokenService(db).rotate(payload.refresh_token)
    return _token_response(pair, must_change_password=False)


@router.post("/logout", status_code=204)
async def logout(payload: LogoutRequest, db: AsyncSession = Depends(get_db)) -> None:
    await TokenService(db).revoke(payload.refresh_token)


@router.post("/password/forgot", response_model=MessageResponse)
async def forgot_password(
    payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    await PasswordService(db).forgot(p_no=payload.p_no)
    return MessageResponse(message="If the account exists, a reset code has been sent")


@router.post("/password/reset/verify-otp", response_model=ChangeTokenResponse)
async def reset_verify_otp(
    payload: OtpVerifyRequest, db: AsyncSession = Depends(get_db)
) -> ChangeTokenResponse:
    token = await PasswordService(db).verify_reset_otp(p_no=payload.p_no, code=payload.code)
    return ChangeTokenResponse(change_token=token, expires_in=300)


@router.post("/password/reset", response_model=MessageResponse)
async def reset_password(
    payload: SetPasswordRequest, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    await PasswordService(db).reset(
        p_no=payload.p_no, change_token=payload.change_token, new_password=payload.new_password
    )
    return MessageResponse(message="Password has been reset")


@router.get("/me", response_model=MeResponse)
async def me(employee: Employee = Depends(get_current_employee)) -> MeResponse:
    return MeResponse.model_validate(employee)
