import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_kitchen_staff
from app.core.database import get_db
from app.models.employee import Employee
from app.repositories.order_repository import OrderRepository
from app.schemas.booking import DelayBookingRequest
from app.schemas.order import OrderRead
from app.services.booking.booking_service import BookingService

router = APIRouter(prefix="/orders/{order_id}/booking", tags=["booking"])

# Separate router: this one is location-scoped, not order-scoped, so it
# can't share the prefix above.
pending_router = APIRouter(tags=["booking"])


@pending_router.get("/locations/{location_id}/bookings/pending", response_model=list[OrderRead])
async def list_pending_bookings(
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(require_kitchen_staff),
) -> list[OrderRead]:
    """Booked orders still awaiting ingredient review -- for the initial
    load of the kitchen/manager screen (the WebSocket "booking.alert" only
    reaches clients already connected when it fires)."""
    orders = await OrderRepository(db).list_pending_bookings_for_location(location_id)
    return [OrderRead.model_validate(o) for o in orders]


@router.post("/confirm-ingredients", response_model=OrderRead)
async def confirm_booking_ingredients(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    staff: Employee = Depends(require_kitchen_staff),
) -> OrderRead:
    order = await BookingService(db).confirm_ingredients(order_id, staff.id)
    return OrderRead.model_validate(order)


@router.post("/delay", response_model=OrderRead)
async def delay_booking(
    order_id: uuid.UUID,
    payload: DelayBookingRequest,
    db: AsyncSession = Depends(get_db),
    staff: Employee = Depends(require_kitchen_staff),
) -> OrderRead:
    order = await BookingService(db).delay_ingredients(
        order_id, staff.id, new_scheduled_for=payload.new_scheduled_for, reason=payload.reason
    )
    return OrderRead.model_validate(order)
