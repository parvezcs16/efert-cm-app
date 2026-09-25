import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_employee
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.employee import Employee
from app.schemas.guest import (
    GuestCreateRequest,
    GuestRead,
    GuestSessionCreateResponse,
    GuestSessionRead,
)
from app.services.guests.guest_service import GuestService

router = APIRouter(prefix="/guests", tags=["guests"])


@router.post("", response_model=GuestRead, status_code=201)
async def register_guest(
    payload: GuestCreateRequest,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
) -> GuestRead:
    guest = await GuestService(db).register(
        host_employee_id=employee.id,
        name=payload.name,
        company_name=payload.company_name,
        cnic=payload.cnic,
        guest_type=payload.guest_type,
        accompanying_persons=payload.accompanying_persons,
    )
    return GuestRead.model_validate(guest)


@router.get("", response_model=list[GuestRead])
async def list_my_guests(
    db: AsyncSession = Depends(get_db), employee: Employee = Depends(get_current_employee)
) -> list[GuestRead]:
    guests = await GuestService(db).list_for_host(employee.id)
    return [GuestRead.model_validate(g) for g in guests]


async def _get_owned_guest(db: AsyncSession, guest_id: uuid.UUID, employee: Employee) -> GuestRead:
    guest = await GuestService(db).get(guest_id)
    if guest.host_employee_id != employee.id:
        raise NotFoundError("Guest not found")
    return GuestRead.model_validate(guest)


@router.get("/{guest_id}", response_model=GuestRead)
async def get_guest(
    guest_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
) -> GuestRead:
    return await _get_owned_guest(db, guest_id, employee)


@router.post("/{guest_id}/sessions", response_model=GuestSessionCreateResponse, status_code=201)
async def open_guest_session(
    guest_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
) -> GuestSessionCreateResponse:
    session, raw_token = await GuestService(db).open_session(
        guest_id=guest_id, host_employee_id=employee.id
    )
    return GuestSessionCreateResponse(
        session=GuestSessionRead.model_validate(session), qr_token=raw_token
    )


@router.get("/{guest_id}/sessions", response_model=list[GuestSessionRead])
async def list_guest_sessions(
    guest_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
) -> list[GuestSessionRead]:
    await _get_owned_guest(db, guest_id, employee)
    sessions = await GuestService(db).list_sessions_for_guest(guest_id)
    return [GuestSessionRead.model_validate(s) for s in sessions]


@router.post("/sessions/{session_id}/close", response_model=GuestSessionRead)
async def close_guest_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
) -> GuestSessionRead:
    session = await GuestService(db).close_session(session_id, employee.id)
    return GuestSessionRead.model_validate(session)


@router.post("/sessions/{session_id}/reopen", response_model=GuestSessionRead)
async def reopen_guest_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
) -> GuestSessionRead:
    session = await GuestService(db).reopen_session(session_id, employee.id)
    return GuestSessionRead.model_validate(session)
