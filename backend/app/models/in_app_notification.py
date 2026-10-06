import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, UUIDPrimaryKeyMixin
from app.models.enums import InAppNotificationType, enum_column


class InAppNotification(UUIDPrimaryKeyMixin, Base):
    """A message shown in an employee's in-app notification inbox (the bell
    in the app header). Separate from `Notification`, which is the delivery
    log for outbound channels like email: this is the inbox itself, owned by
    an employee and tracked read/unread.

    `dedupe_key`, when set, makes creation idempotent -- e.g. one daily
    served summary per employee per day even if the scheduler runs twice.
    NULLs don't collide under a Postgres unique constraint, so one-off
    notifications simply leave it unset."""

    __tablename__ = "in_app_notifications"
    __table_args__ = (
        Index("ix_in_app_notifications_employee_created", "employee_id", "created_at"),
    )

    employee_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )
    type: Mapped[InAppNotificationType] = mapped_column(
        enum_column(InAppNotificationType, "in_app_notification_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(String(2000), nullable=False)
    # In-app route to open when the notification is clicked, e.g. "/guests".
    link: Mapped[str | None] = mapped_column(String(300))
    dedupe_key: Mapped[str | None] = mapped_column(String(200), unique=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
