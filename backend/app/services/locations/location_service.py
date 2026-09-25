import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.enums import ActiveStatus, EmployeeRole
from app.models.location import Location
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.location_repository import LocationRepository
from app.services.audit_service import AuditService

MANAGER_ELIGIBLE_ROLES = (
    EmployeeRole.LOCATION_MANAGER,
    EmployeeRole.SYSTEM_MANAGER,
    EmployeeRole.SYSTEM_ADMINISTRATOR,
)


class LocationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.locations = LocationRepository(db)
        self.employees = EmployeeRepository(db)
        self.audit = AuditService(db)

    async def create(self, *, name: str, code: str, created_by_id: uuid.UUID) -> Location:
        if await self.locations.get_by_code(code) is not None:
            raise ConflictError("A location with this code already exists")

        location = Location(name=name, code=code)
        self.locations.add(location)
        await self.locations.flush()

        await self.audit.record(
            action="location.created",
            entity_type="location",
            entity_id=str(location.id),
            actor_employee_id=created_by_id,
            new_values={"name": name, "code": code},
        )
        return location

    async def get(self, location_id: uuid.UUID) -> Location:
        location = await self.locations.get_by_id(location_id)
        if location is None:
            raise NotFoundError("Location not found")
        return location

    async def list_all(self) -> list[Location]:
        return await self.locations.list_all()

    async def update(
        self,
        *,
        location_id: uuid.UUID,
        name: str | None,
        status: ActiveStatus | None,
        manager_id: uuid.UUID | None,
        updated_by_id: uuid.UUID,
    ) -> Location:
        location = await self.get(location_id)
        old_values = {
            "name": location.name,
            "status": location.status.value,
            "manager_id": str(location.manager_id) if location.manager_id else None,
        }

        if name is not None:
            location.name = name
        if status is not None:
            location.status = status
        if manager_id is not None:
            manager = await self.employees.get_by_id(manager_id)
            if manager is None:
                raise ValidationAppError("Manager not found")
            if manager.role not in MANAGER_ELIGIBLE_ROLES:
                raise ValidationAppError(
                    "Employee does not have a role eligible to manage a location"
                )
            location.manager_id = manager_id

        await self.locations.flush()
        await self.audit.record(
            action="location.updated",
            entity_type="location",
            entity_id=str(location.id),
            actor_employee_id=updated_by_id,
            old_values=old_values,
            new_values={
                "name": location.name,
                "status": location.status.value,
                "manager_id": str(location.manager_id) if location.manager_id else None,
            },
        )
        return location
