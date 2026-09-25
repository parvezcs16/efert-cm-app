from datetime import datetime

from pydantic import BaseModel, Field


class DelayBookingRequest(BaseModel):
    new_scheduled_for: datetime
    reason: str = Field(min_length=1, max_length=500)
