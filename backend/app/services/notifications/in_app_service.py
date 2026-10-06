import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.enums import InAppNotificationType
from app.models.in_app_notification import InAppNotification
from app.repositories.in_app_notification_repository import InAppNotificationRepository

INBOX_LIMIT = 50


class InAppNotificationService:
    """An employee's in-app notification inbox. Producers (guest reopen
    requests, the daily served summary, ...) call `notify`; the employee
    reads and acknowledges them through the /notifications endpoints."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.notifications = InAppNotificationRepository(db)

    async def notify(
        self,
        *,
        employee_id: uuid.UUID,
        type: InAppNotificationType,
        title: str,
        body: str,
        link: str | None = None,
        dedupe_key: str | None = None,
    ) -> InAppNotification:
        notification = InAppNotification(
            employee_id=employee_id,
            type=type,
            title=title,
            body=body,
            link=link,
            dedupe_key=dedupe_key,
        )
        self.notifications.add(notification)
        await self.notifications.flush()
        return notification

    async def list_for_employee(self, employee_id: uuid.UUID) -> list[InAppNotification]:
        return await self.notifications.list_for_employee(employee_id, limit=INBOX_LIMIT)

    async def unread_count(self, employee_id: uuid.UUID) -> int:
        return await self.notifications.count_unread(employee_id)

    async def mark_read(
        self, notification_id: uuid.UUID, employee_id: uuid.UUID
    ) -> InAppNotification:
        notification = await self.notifications.get_by_id(notification_id)
        # Someone else's notification is indistinguishable from a missing one.
        if notification is None or notification.employee_id != employee_id:
            raise NotFoundError("Notification not found")
        if notification.read_at is None:
            notification.read_at = datetime.now(UTC)
            await self.notifications.flush()
        return notification

    async def mark_all_read(self, employee_id: uuid.UUID) -> None:
        await self.notifications.mark_all_read(employee_id, datetime.now(UTC))
