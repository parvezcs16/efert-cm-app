import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import RegistrationStatus
from app.schemas.employee import EmployeeRead

P_NO_PATTERN = r"^[A-Za-z0-9-]{3,20}$"
OTP_PATTERN = r"^\d{6}$"


def _validate_password_strength(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not any(c.isalpha() for c in value):
        raise ValueError("Password must contain at least one letter")
    if not any(c.isdigit() for c in value):
        raise ValueError("Password must contain at least one digit")
    return value


class RegistrationRequest(BaseModel):
    p_no: str = Field(pattern=P_NO_PATTERN)
    email: EmailStr
    name: str = Field(min_length=1, max_length=200)
    department: str | None = None


class RegistrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    p_no: str
    email: str
    name: str
    status: RegistrationStatus


class RegistrationDecisionRequest(BaseModel):
    reason: str | None = None


class ActivationStartRequest(BaseModel):
    p_no: str = Field(pattern=P_NO_PATTERN)
    temporary_password: str


class OtpVerifyRequest(BaseModel):
    p_no: str = Field(pattern=P_NO_PATTERN)
    code: str = Field(pattern=OTP_PATTERN)


class ChangeTokenResponse(BaseModel):
    change_token: str
    expires_in: int


class SetPasswordRequest(BaseModel):
    p_no: str = Field(pattern=P_NO_PATTERN)
    change_token: str
    new_password: str

    _validate_new_password = field_validator("new_password")(_validate_password_strength)


class LoginRequest(BaseModel):
    p_no: str = Field(pattern=P_NO_PATTERN)
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    must_change_password: bool


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    p_no: str = Field(pattern=P_NO_PATTERN)


class MessageResponse(BaseModel):
    message: str


class MeResponse(EmployeeRead):
    pass
