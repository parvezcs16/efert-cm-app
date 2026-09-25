import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consumption import ConsumptionRecord


class ConsumptionRecordRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_order_item(self, order_item_id: uuid.UUID) -> ConsumptionRecord | None:
        result = await self.db.execute(
            select(ConsumptionRecord).where(ConsumptionRecord.order_item_id == order_item_id)
        )
        return result.scalar_one_or_none()

    async def list_by_order_items(
        self, order_item_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, ConsumptionRecord]:
        if not order_item_ids:
            return {}
        result = await self.db.execute(
            select(ConsumptionRecord).where(ConsumptionRecord.order_item_id.in_(order_item_ids))
        )
        return {r.order_item_id: r for r in result.scalars().all()}

    def add(self, record: ConsumptionRecord) -> None:
        self.db.add(record)

    async def flush(self) -> None:
        await self.db.flush()
