from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, UUIDPrimaryKeyMixin
from app.models.enums import NotificationChannel, NotificationStatus, enum_column


class Notification(UUIDPrimaryKeyMixin, Base):
    """Persistent record of every notification attempt, so delivery can be
    audited/retried later -- not just a log line (docs/database.md
    "Notification"). Written by NotificationDispatchService, which wraps
    the underlying channel sender (see app/services/notifications)."""

    __tablename__ = "notifications"

    recipient: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    channel: Mapped[NotificationChannel] = mapped_column(
        enum_column(NotificationChannel, "notification_channel"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(
        enum_column(NotificationStatus, "notification_status"), nullable=False
    )
    payload_reference: Mapped[str | None] = mapped_column(String(200))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
