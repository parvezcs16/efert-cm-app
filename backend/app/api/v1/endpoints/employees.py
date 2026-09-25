import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_employee, require_roles
from app.core.database import get_db
from app.models.employee import Employee
from app.models.enums import EmployeeRole
from app.schemas.billing import StatementFrequencyUpdateRequest
from app.schemas.employee import EmployeeCreateRequest, EmployeeCreateResponse, EmployeeRead
from app.services.employees.employee_service import EmployeeService
from app.services.notifications.dispatch_service import NotificationDispatchService

router = APIRouter(prefix="/employees", tags=["employees"])

EMPLOYEE_ADMIN_ROLES = (EmployeeRole.SYSTEM_MANAGER, EmployeeRole.SYSTEM_ADMINISTRATOR)


@router.post("", response_model=EmployeeCreateResponse, status_code=201)
async def create_employee(
    payload: EmployeeCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: Employee = Depends(require_roles(*EMPLOYEE_ADMIN_ROLES)),
) -> EmployeeCreateResponse:
    employee, temporary_password = await EmployeeService(db).create_by_admin(
        p_no=payload.p_no,
        name=payload.name,
        email=payload.email,
        department=payload.department,
        role=payload.role,
        created_by_id=admin.id,
    )
    await NotificationDispatchService(db).send_email(
        to=employee.email,
        subject="Your mess account has been created",
        body=(
            f"Your P-Number is {employee.p_no} and temporary password is "
            f"{temporary_password}. Use it to activate your account."
        ),
        type="EMPLOYEE_CREATED_BY_ADMIN",
        payload_reference=str(employee.id),
    )
    return EmployeeCreateResponse(
        employee=EmployeeRead.model_validate(employee), temporary_password=temporary_password
    )


@router.get("/me", response_model=EmployeeRead)
async def get_my_profile(employee: Employee = Depends(get_current_employee)) -> EmployeeRead:
    return EmployeeRead.model_validate(employee)


@router.patch("/me/statement-frequency", response_model=EmployeeRead)
async def update_my_statement_frequency(
    payload: StatementFrequencyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
) -> EmployeeRead:
    updated = await EmployeeService(db).update_statement_frequency(employee.id, payload.frequency)
    return EmployeeRead.model_validate(updated)


@router.get("", response_model=list[EmployeeRead])
async def search_employees(
    q: str | None = Query(default=None, description="Matches P-Number or name, substring"),
    role: list[EmployeeRole] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(require_roles(*EMPLOYEE_ADMIN_ROLES)),
) -> list[EmployeeRead]:
    """Employee directory lookup for admin screens -- e.g. picking a
    location manager by name instead of pasting a raw employee ID."""
    employees = await EmployeeService(db).search(q=q, roles=role)
    return [EmployeeRead.model_validate(e) for e in employees]


@router.get("/{employee_id}", response_model=EmployeeRead)
async def get_employee(
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(require_roles(*EMPLOYEE_ADMIN_ROLES)),
) -> EmployeeRead:
    employee = await EmployeeService(db).get(employee_id)
    return EmployeeRead.model_validate(employee)
