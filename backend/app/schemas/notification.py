import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import InAppNotificationType


class InAppNotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: InAppNotificationType
    title: str
    body: str
    link: str | None
    read_at: datetime | None
    created_at: datetime


class UnreadCountRead(BaseModel):
    unread: int
