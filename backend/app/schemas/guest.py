import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import GuestSessionStatus, GuestType


class GuestCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    company_name: str = Field(min_length=1, max_length=200)
    cnic: str = Field(min_length=1, max_length=20)
    guest_type: GuestType
    accompanying_persons: int = Field(default=0, ge=0, le=50)


class GuestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    host_employee_id: uuid.UUID
    name: str
    company_name: str
    cnic: str
    guest_type: GuestType
    accompanying_persons: int
    created_at: datetime


class GuestSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    guest_id: uuid.UUID
    host_employee_id: uuid.UUID
    status: GuestSessionStatus
    opened_at: datetime
    closed_at: datetime | None
    token_expires_at: datetime


class GuestSessionCreateResponse(BaseModel):
    """`qr_token` is the plaintext bearer token to encode in the QR code --
    shown exactly once, here, and never retrievable again (only its hash is
    stored)."""

    session: GuestSessionRead
    qr_token: str


class GuestAuthRequest(BaseModel):
    token: str


class GuestAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    session: GuestSessionRead
