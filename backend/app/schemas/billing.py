import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import LedgerEntryType, LedgerSourceType, StatementFrequency


class LedgerEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_type: LedgerSourceType
    entry_type: LedgerEntryType
    amount: Decimal
    reason: str
    guest_session_id: uuid.UUID | None
    created_at: datetime


class StatementResponse(BaseModel):
    entries: list[LedgerEntryRead]
    total_debit: Decimal
    total_credit: Decimal
    net_balance: Decimal


class StatementFrequencyUpdateRequest(BaseModel):
    frequency: StatementFrequency


class EmployeeAdjustmentRequest(BaseModel):
    source_type: LedgerSourceType = Field(
        description="PERSONAL_CONSUMPTION or PRIVATE_GUEST -- which bucket of the "
        "employee's account this adjustment applies to."
    )
    entry_type: LedgerEntryType
    amount: Decimal = Field(gt=0, decimal_places=2)
    reason: str = Field(min_length=1, max_length=500)
    reversal_of_id: uuid.UUID | None = None


class OfficialAdjustmentRequest(BaseModel):
    entry_type: LedgerEntryType
    amount: Decimal = Field(gt=0, decimal_places=2)
    reason: str = Field(min_length=1, max_length=500)
    reversal_of_id: uuid.UUID | None = None
