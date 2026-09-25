import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import (
    SYSTEM_LEVEL_ROLES,
    get_current_employee,
    require_location_authority,
    require_roles,
)
from app.core.database import get_db
from app.models.employee import Employee
from app.schemas.location import (
    KitchenStationCreateRequest,
    KitchenStationRead,
    KitchenStationUpdateRequest,
    LocationCreateRequest,
    LocationRead,
    LocationUpdateRequest,
)
from app.services.locations.kitchen_station_service import KitchenStationService
from app.services.locations.location_service import LocationService

router = APIRouter(prefix="/locations", tags=["locations"])


@router.post("", response_model=LocationRead, status_code=201)
async def create_location(
    payload: LocationCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: Employee = Depends(require_roles(*SYSTEM_LEVEL_ROLES)),
) -> LocationRead:
    location = await LocationService(db).create(
        name=payload.name, code=payload.code, created_by_id=admin.id
    )
    return LocationRead.model_validate(location)


@router.get("", response_model=list[LocationRead])
async def list_locations(
    db: AsyncSession = Depends(get_db), _: Employee = Depends(get_current_employee)
) -> list[LocationRead]:
    locations = await LocationService(db).list_all()
    return [LocationRead.model_validate(location) for location in locations]


@router.get("/{location_id}", response_model=LocationRead)
async def get_location(
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(get_current_employee),
) -> LocationRead:
    location = await LocationService(db).get(location_id)
    return LocationRead.model_validate(location)


@router.patch("/{location_id}", response_model=LocationRead)
async def update_location(
    location_id: uuid.UUID,
    payload: LocationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: Employee = Depends(require_roles(*SYSTEM_LEVEL_ROLES)),
) -> LocationRead:
    location = await LocationService(db).update(
        location_id=location_id,
        name=payload.name,
        status=payload.status,
        manager_id=payload.manager_id,
        updated_by_id=admin.id,
    )
    return LocationRead.model_validate(location)


@router.post(
    "/{location_id}/kitchen-stations", response_model=KitchenStationRead, status_code=201
)
async def create_kitchen_station(
    location_id: uuid.UUID,
    payload: KitchenStationCreateRequest,
    db: AsyncSession = Depends(get_db),
    manager: Employee = Depends(require_location_authority),
) -> KitchenStationRead:
    station = await KitchenStationService(db).create(
        location_id=location_id, name=payload.name, created_by_id=manager.id
    )
    return KitchenStationRead.model_validate(station)


@router.get("/{location_id}/kitchen-stations", response_model=list[KitchenStationRead])
async def list_kitchen_stations(
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(get_current_employee),
) -> list[KitchenStationRead]:
    stations = await KitchenStationService(db).list_for_location(location_id)
    return [KitchenStationRead.model_validate(station) for station in stations]


@router.patch(
    "/{location_id}/kitchen-stations/{station_id}", response_model=KitchenStationRead
)
async def update_kitchen_station(
    location_id: uuid.UUID,
    station_id: uuid.UUID,
    payload: KitchenStationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    manager: Employee = Depends(require_location_authority),
) -> KitchenStationRead:
    station = await KitchenStationService(db).update(
        station_id=station_id, name=payload.name, status=payload.status, updated_by_id=manager.id
    )
    return KitchenStationRead.model_validate(station)
