from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


class NotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, notification: Notification) -> None:
        self.db.add(notification)

    async def flush(self) -> None:
        await self.db.flush()

    async def latest_created_at(
        self, *, type: str, payload_reference: str
    ) -> datetime | None:
        """When the most recent notification of `type` about
        `payload_reference` was recorded, e.g. to rate-limit repeat sends."""
        result = await self.db.execute(
            select(Notification.created_at)
            .where(
                Notification.type == type,
                Notification.payload_reference == payload_reference,
            )
            .order_by(Notification.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
