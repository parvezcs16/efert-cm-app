import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.enums import ActiveStatus
from app.models.location import KitchenStation
from app.repositories.location_repository import KitchenStationRepository, LocationRepository
from app.services.audit_service import AuditService


class KitchenStationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.stations = KitchenStationRepository(db)
        self.locations = LocationRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, *, location_id: uuid.UUID, name: str, created_by_id: uuid.UUID
    ) -> KitchenStation:
        if await self.locations.get_by_id(location_id) is None:
            raise NotFoundError("Location not found")

        station = KitchenStation(location_id=location_id, name=name)
        self.stations.add(station)
        await self.stations.flush()

        await self.audit.record(
            action="kitchen_station.created",
            entity_type="kitchen_station",
            entity_id=str(station.id),
            actor_employee_id=created_by_id,
            new_values={"location_id": str(location_id), "name": name},
        )
        return station

    async def list_for_location(self, location_id: uuid.UUID) -> list[KitchenStation]:
        return await self.stations.list_for_location(location_id)

    async def update(
        self,
        *,
        station_id: uuid.UUID,
        name: str | None,
        status: ActiveStatus | None,
        updated_by_id: uuid.UUID,
    ) -> KitchenStation:
        station = await self.stations.get_by_id(station_id)
        if station is None:
            raise NotFoundError("Kitchen station not found")

        if name is not None:
            station.name = name
        if status is not None:
            station.status = status
        await self.stations.flush()

        await self.audit.record(
            action="kitchen_station.updated",
            entity_type="kitchen_station",
            entity_id=str(station.id),
            actor_employee_id=updated_by_id,
        )
        return station
