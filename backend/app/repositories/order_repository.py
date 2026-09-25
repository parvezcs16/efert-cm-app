import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import text

from app.models.enums import IngredientStatus, OrderStatus, OrderType
from app.models.order import Order


class OrderRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def next_order_number(self) -> str:
        result = await self.db.execute(text("SELECT nextval('order_number_seq')"))
        value = result.scalar_one()
        return f"ORD-{value:06d}"

    async def get_by_id(self, order_id: uuid.UUID) -> Order | None:
        result = await self.db.execute(
            select(Order).where(Order.id == order_id).options(selectinload(Order.items))
        )
        return result.scalar_one_or_none()

    async def list_for_employee(self, employee_id: uuid.UUID) -> list[Order]:
        result = await self.db.execute(
            select(Order)
            .where(Order.employee_id == employee_id)
            .options(selectinload(Order.items))
            .order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_for_guest_session(self, guest_session_id: uuid.UUID) -> list[Order]:
        result = await self.db.execute(
            select(Order)
            .where(Order.guest_session_id == guest_session_id)
            .options(selectinload(Order.items))
            .order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_for_location_by_status(
        self, location_id: uuid.UUID, statuses: list[OrderStatus]
    ) -> list[Order]:
        result = await self.db.execute(
            select(Order)
            .where(Order.location_id == location_id, Order.status.in_(statuses))
            .options(selectinload(Order.items))
            .order_by(Order.created_at)
        )
        return list(result.scalars().all())

    async def list_for_location_in_period(
        self, location_id: uuid.UUID, *, since: datetime, until: datetime
    ) -> list[Order]:
        result = await self.db.execute(
            select(Order)
            .where(
                Order.location_id == location_id,
                Order.created_at >= since,
                Order.created_at <= until,
            )
            .options(selectinload(Order.items))
            .order_by(Order.created_at)
        )
        return list(result.scalars().all())

    async def list_pending_bookings_for_location(self, location_id: uuid.UUID) -> list[Order]:
        """Booked orders still awaiting ingredient review (PENDING or
        DELAYED) -- for the kitchen/manager screen's initial load, since
        the WebSocket "booking.alert" only reaches clients already
        connected when it fires."""
        result = await self.db.execute(
            select(Order)
            .where(
                Order.location_id == location_id,
                Order.order_type == OrderType.BOOK_FOR_LATER,
                Order.ingredient_status.in_([IngredientStatus.PENDING, IngredientStatus.DELAYED]),
            )
            .options(selectinload(Order.items))
            .order_by(Order.scheduled_for)
        )
        return list(result.scalars().all())

    def add(self, order: Order) -> None:
        self.db.add(order)

    async def flush(self) -> None:
        await self.db.flush()
