import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, entry: AuditLog) -> None:
        self.db.add(entry)

    async def search(
        self,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        actor_employee_id: uuid.UUID | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 200,
    ) -> list[AuditLog]:
        query = select(AuditLog)
        if entity_type is not None:
            query = query.where(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            query = query.where(AuditLog.entity_id == entity_id)
        if actor_employee_id is not None:
            query = query.where(AuditLog.actor_employee_id == actor_employee_id)
        if since is not None:
            query = query.where(AuditLog.created_at >= since)
        if until is not None:
            query = query.where(AuditLog.created_at <= until)
        query = query.order_by(AuditLog.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())
