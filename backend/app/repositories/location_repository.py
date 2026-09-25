import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import KitchenStation, Location


class LocationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, location_id: uuid.UUID) -> Location | None:
        return await self.db.get(Location, location_id)

    async def get_by_code(self, code: str) -> Location | None:
        result = await self.db.execute(select(Location).where(Location.code == code))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Location]:
        result = await self.db.execute(select(Location).order_by(Location.name))
        return list(result.scalars().all())

    def add(self, location: Location) -> None:
        self.db.add(location)

    async def flush(self) -> None:
        await self.db.flush()


class KitchenStationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, station_id: uuid.UUID) -> KitchenStation | None:
        return await self.db.get(KitchenStation, station_id)

    async def list_for_location(self, location_id: uuid.UUID) -> list[KitchenStation]:
        result = await self.db.execute(
            select(KitchenStation)
            .where(KitchenStation.location_id == location_id)
            .order_by(KitchenStation.name)
        )
        return list(result.scalars().all())

    def add(self, station: KitchenStation) -> None:
        self.db.add(station)

    async def flush(self) -> None:
        await self.db.flush()
