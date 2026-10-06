import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.in_app_notification import InAppNotification


class InAppNotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, notification: InAppNotification) -> None:
        self.db.add(notification)

    async def flush(self) -> None:
        await self.db.flush()

    async def get_by_id(self, notification_id: uuid.UUID) -> InAppNotification | None:
        return await self.db.get(InAppNotification, notification_id)

    async def list_for_employee(
        self, employee_id: uuid.UUID, *, limit: int
    ) -> list[InAppNotification]:
        result = await self.db.execute(
            select(InAppNotification)
            .where(InAppNotification.employee_id == employee_id)
            .order_by(InAppNotification.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_unread(self, employee_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(InAppNotification)
            .where(
                InAppNotification.employee_id == employee_id,
                InAppNotification.read_at.is_(None),
            )
        )
        return int(result.scalar_one())

    async def mark_all_read(self, employee_id: uuid.UUID, now: datetime) -> None:
        await self.db.execute(
            update(InAppNotification)
            .where(
                InAppNotification.employee_id == employee_id,
                InAppNotification.read_at.is_(None),
            )
            .values(read_at=now)
        )

    async def existing_dedupe_keys(self, keys: list[str]) -> set[str]:
        if not keys:
            return set()
        result = await self.db.execute(
            select(InAppNotification.dedupe_key).where(InAppNotification.dedupe_key.in_(keys))
        )
        return {key for key in result.scalars().all() if key is not None}
