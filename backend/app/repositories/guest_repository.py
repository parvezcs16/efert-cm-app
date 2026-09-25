import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guest import Guest, GuestSession


class GuestRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, guest_id: uuid.UUID) -> Guest | None:
        return await self.db.get(Guest, guest_id)

    async def list_for_host(self, host_employee_id: uuid.UUID) -> list[Guest]:
        result = await self.db.execute(
            select(Guest)
            .where(Guest.host_employee_id == host_employee_id)
            .order_by(Guest.created_at.desc())
        )
        return list(result.scalars().all())

    def add(self, guest: Guest) -> None:
        self.db.add(guest)

    async def flush(self) -> None:
        await self.db.flush()


class GuestSessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, session_id: uuid.UUID) -> GuestSession | None:
        return await self.db.get(GuestSession, session_id)

    async def get_by_token_hash(self, token_hash: str) -> GuestSession | None:
        result = await self.db.execute(
            select(GuestSession).where(GuestSession.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def list_for_guest(self, guest_id: uuid.UUID) -> list[GuestSession]:
        result = await self.db.execute(
            select(GuestSession)
            .where(GuestSession.guest_id == guest_id)
            .order_by(GuestSession.opened_at.desc())
        )
        return list(result.scalars().all())

    def add(self, session: GuestSession) -> None:
        self.db.add(session)

    async def flush(self) -> None:
        await self.db.flush()
