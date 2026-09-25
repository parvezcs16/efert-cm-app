import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ConsumptionStatus


class CorrectionRequestPayload(BaseModel):
    requested_quantity: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=500)


class CorrectionValidatePayload(BaseModel):
    approve: bool


class ConsumptionRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_item_id: uuid.UUID
    served_quantity: int
    status: ConsumptionStatus
    served_at: datetime
    requested_quantity: int | None
    requested_reason: str | None
