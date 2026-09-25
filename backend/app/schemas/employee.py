import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import EmployeeRole, EmployeeStatus, PasswordState, StatementFrequency


class EmployeeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    p_no: str
    name: str
    email: EmailStr
    department: str | None
    status: EmployeeStatus
    role: EmployeeRole
    password_state: PasswordState
    statement_frequency: StatementFrequency
    next_statement_due_at: datetime | None
    created_at: datetime


class EmployeeCreateRequest(BaseModel):
    """Admin-created employee. Skips the self-registration approval step but
    still requires the normal OTP + mandatory password change on first use."""

    p_no: str
    name: str
    email: EmailStr
    department: str | None = None
    role: EmployeeRole = EmployeeRole.EMPLOYEE


class EmployeeCreateResponse(BaseModel):
    employee: EmployeeRead
    temporary_password: str
