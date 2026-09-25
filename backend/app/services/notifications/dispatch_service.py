from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.enums import NotificationChannel, NotificationStatus
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository
from app.services.notifications import get_notification_sender

logger = get_logger("notifications.dispatch")


class NotificationDispatchService:
    """Wraps the channel-agnostic NotificationSender (app/services/
    notifications/base.py) with a persistent record of every attempt, so
    delivery can be audited or retried later instead of only existing as a
    log line (docs/database.md "Notification"). All email sends in the app
    should go through this rather than calling the sender directly."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.notifications = NotificationRepository(db)
        self.sender = get_notification_sender()

    async def send_email(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        type: str,
        payload_reference: str | None = None,
    ) -> Notification:
        notification = Notification(
            recipient=to,
            channel=NotificationChannel.EMAIL,
            type=type,
            status=NotificationStatus.SENT,
            payload_reference=payload_reference,
            sent_at=datetime.now(UTC),
        )
        try:
            await self.sender.send_email(to=to, subject=subject, body=body)
        except Exception:
            logger.warning("Notification delivery failed: type=%s to=%s", type, to, exc_info=True)
            notification.status = NotificationStatus.FAILED
            notification.sent_at = None

        self.notifications.add(notification)
        await self.notifications.flush()
        return notification
