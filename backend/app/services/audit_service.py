import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = AuditRepository(db)

    async def record(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        actor_employee_id: uuid.UUID | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
    ) -> None:
        self.repo.add(
            AuditLog(
                actor_employee_id=actor_employee_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                old_values=old_values,
                new_values=new_values,
            )
        )

    async def search(
        self,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        actor_employee_id: uuid.UUID | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[AuditLog]:
        return await self.repo.search(
            entity_type=entity_type,
            entity_id=entity_id,
            actor_employee_id=actor_employee_id,
            since=since,
            until=until,
        )
