import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_kitchen_staff
from app.core.database import get_db
from app.models.employee import Employee
from app.schemas.order import OrderRead, QueueOrderRequest
from app.services.kitchen.kitchen_service import KitchenService

router = APIRouter(tags=["kitchen"])


@router.post("/orders/{order_id}/confirm", response_model=OrderRead)
async def confirm_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    staff: Employee = Depends(require_kitchen_staff),
) -> OrderRead:
    order = await KitchenService(db).confirm(order_id, staff.id)
    return OrderRead.model_validate(order)


@router.post("/orders/{order_id}/queue", response_model=OrderRead)
async def queue_order(
    order_id: uuid.UUID,
    payload: QueueOrderRequest,
    db: AsyncSession = Depends(get_db),
    staff: Employee = Depends(require_kitchen_staff),
) -> OrderRead:
    order = await KitchenService(db).queue(order_id, staff.id, payload.station_assignments)
    return OrderRead.model_validate(order)


@router.post("/orders/{order_id}/start-preparing", response_model=OrderRead)
async def start_preparing(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    staff: Employee = Depends(require_kitchen_staff),
) -> OrderRead:
    order = await KitchenService(db).start_preparing(order_id, staff.id)
    return OrderRead.model_validate(order)


@router.post("/orders/{order_id}/mark-ready", response_model=OrderRead)
async def mark_ready(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    staff: Employee = Depends(require_kitchen_staff),
) -> OrderRead:
    order = await KitchenService(db).mark_ready(order_id, staff.id)
    return OrderRead.model_validate(order)


@router.post("/orders/{order_id}/serve", response_model=OrderRead)
async def serve_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    staff: Employee = Depends(require_kitchen_staff),
) -> OrderRead:
    order = await KitchenService(db).serve(order_id, staff.id)
    return OrderRead.model_validate(order)


@router.post("/orders/{order_id}/serve-directly", response_model=OrderRead)
async def serve_order_directly(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    staff: Employee = Depends(require_kitchen_staff),
) -> OrderRead:
    order = await KitchenService(db).serve_directly(order_id, staff.id)
    return OrderRead.model_validate(order)


@router.get("/locations/{location_id}/orders/incoming", response_model=list[OrderRead])
async def get_incoming_orders(
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(require_kitchen_staff),
) -> list[OrderRead]:
    orders = await KitchenService(db).get_incoming_orders(location_id)
    return [OrderRead.model_validate(o) for o in orders]


@router.get(
    "/locations/{location_id}/kitchen-stations/{station_id}/queue",
    response_model=list[OrderRead],
)
async def get_station_queue(
    location_id: uuid.UUID,
    station_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(require_kitchen_staff),
) -> list[OrderRead]:
    orders = await KitchenService(db).get_station_queue(location_id, station_id)
    return [OrderRead.model_validate(o) for o in orders]
