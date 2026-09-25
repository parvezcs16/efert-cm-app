from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


class NotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, notification: Notification) -> None:
        self.db.add(notification)

    async def flush(self) -> None:
        await self.db.flush()
