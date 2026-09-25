import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_employee
from app.core.database import get_db
from app.models.employee import Employee
from app.schemas.order import OrderCreateRequest, OrderRead
from app.services.ordering.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=201)
async def create_order(
    payload: OrderCreateRequest,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
) -> OrderRead:
    order = await OrderService(db).create_employee_order(
        employee_id=employee.id,
        location_id=payload.location_id,
        order_type=payload.order_type,
        scheduled_for=payload.scheduled_for,
        items=[(item.menu_item_id, item.quantity) for item in payload.items],
    )
    return OrderRead.model_validate(order)


@router.get("", response_model=list[OrderRead])
async def list_my_orders(
    db: AsyncSession = Depends(get_db), employee: Employee = Depends(get_current_employee)
) -> list[OrderRead]:
    orders = await OrderService(db).list_for_employee(employee.id)
    return [OrderRead.model_validate(o) for o in orders]


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
) -> OrderRead:
    order = await OrderService(db).get_owned(order_id, employee.id)
    return OrderRead.model_validate(order)


@router.post("/{order_id}/cancel", response_model=OrderRead)
async def cancel_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
) -> OrderRead:
    order = await OrderService(db).cancel(order_id, employee.id)
    return OrderRead.model_validate(order)
