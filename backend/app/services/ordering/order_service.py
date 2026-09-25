import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.enums import (
    ActiveStatus,
    CustomerType,
    GuestSessionStatus,
    IngredientStatus,
    OrderStatus,
    OrderType,
)
from app.models.order import Order, OrderItem
from app.repositories.guest_repository import GuestSessionRepository
from app.repositories.location_repository import LocationRepository
from app.repositories.order_repository import OrderRepository
from app.services.audit_service import AuditService
from app.services.menu.menu_service import MenuService
from app.websocket.manager import kitchen_ws_manager

# "Cancellation is permitted before serving" (docs/ordering.md) -- any
# non-terminal status may still be cancelled.
CANCELLABLE_STATUSES = {
    OrderStatus.PENDING,
    OrderStatus.CONFIRMED,
    OrderStatus.QUEUED,
    OrderStatus.PREPARING,
    OrderStatus.READY,
}


class OrderService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.orders = OrderRepository(db)
        self.locations = LocationRepository(db)
        self.guest_sessions = GuestSessionRepository(db)
        self.menu = MenuService(db)
        self.audit = AuditService(db)

    async def _validate_location_and_schedule(
        self, *, location_id: uuid.UUID, order_type: OrderType, scheduled_for: datetime | None
    ) -> None:
        location = await self.locations.get_by_id(location_id)
        if location is None or location.status != ActiveStatus.ACTIVE:
            raise ValidationAppError("Location not found or not active")

        if order_type == OrderType.BOOK_FOR_LATER:
            assert scheduled_for is not None  # enforced by the request schema
            if scheduled_for <= datetime.now(UTC):
                raise ValidationAppError("scheduled_for must be in the future")

    async def _build_order_items(
        self, *, location_id: uuid.UUID, items: list[tuple[uuid.UUID, int]]
    ) -> list[OrderItem]:
        order_items: list[OrderItem] = []
        for menu_item_id, quantity in items:
            price = await self.menu.get_sellable_price(
                menu_item_id=menu_item_id, location_id=location_id
            )
            if price is None:
                raise ValidationAppError(
                    f"Menu item {menu_item_id} is not available at this location"
                )
            order_items.append(
                OrderItem(menu_item_id=menu_item_id, ordered_quantity=quantity, unit_price=price)
            )
        return order_items

    async def _after_booked_order_created(self, order: Order) -> None:
        """Booked orders need ingredient confirmation before they can enter
        the kitchen pipeline (Phase 7); alert management immediately since
        "a booked order is visible to management/kitchen immediately"."""
        if order.order_type != OrderType.BOOK_FOR_LATER:
            return

        order.ingredient_status = IngredientStatus.PENDING
        await self.orders.flush()
        await kitchen_ws_manager.broadcast(
            order.location_id,
            {
                "type": "booking.alert",
                "order_id": str(order.id),
                "order_number": order.order_number,
                "scheduled_for": order.scheduled_for.isoformat() if order.scheduled_for else None,
            },
        )

    async def create_employee_order(
        self,
        *,
        employee_id: uuid.UUID,
        location_id: uuid.UUID,
        order_type: OrderType,
        scheduled_for: datetime | None,
        items: list[tuple[uuid.UUID, int]],
    ) -> Order:
        await self._validate_location_and_schedule(
            location_id=location_id, order_type=order_type, scheduled_for=scheduled_for
        )
        order_items = await self._build_order_items(location_id=location_id, items=items)

        order = Order(
            order_number=await self.orders.next_order_number(),
            location_id=location_id,
            customer_type=CustomerType.EMPLOYEE,
            employee_id=employee_id,
            order_type=order_type,
            scheduled_for=scheduled_for,
            status=OrderStatus.PENDING,
            items=order_items,
        )
        self.orders.add(order)
        await self.orders.flush()
        await self._after_booked_order_created(order)

        await self.audit.record(
            action="order.created",
            entity_type="order",
            entity_id=str(order.id),
            actor_employee_id=employee_id,
            new_values={"order_type": order_type.value, "item_count": len(order_items)},
        )
        return order

    async def create_guest_order(
        self,
        *,
        guest_session_id: uuid.UUID,
        location_id: uuid.UUID,
        order_type: OrderType,
        scheduled_for: datetime | None,
        items: list[tuple[uuid.UUID, int]],
    ) -> Order:
        session = await self.guest_sessions.get_by_id(guest_session_id)
        if session is None:
            raise NotFoundError("Guest session not found")
        if session.status != GuestSessionStatus.ACTIVE:
            raise ValidationAppError("This guest session is closed and cannot place new orders")

        await self._validate_location_and_schedule(
            location_id=location_id, order_type=order_type, scheduled_for=scheduled_for
        )
        order_items = await self._build_order_items(location_id=location_id, items=items)

        order = Order(
            order_number=await self.orders.next_order_number(),
            location_id=location_id,
            customer_type=CustomerType.GUEST,
            guest_session_id=guest_session_id,
            order_type=order_type,
            scheduled_for=scheduled_for,
            status=OrderStatus.PENDING,
            items=order_items,
        )
        self.orders.add(order)
        await self.orders.flush()
        await self._after_booked_order_created(order)

        await self.audit.record(
            action="order.created",
            entity_type="order",
            entity_id=str(order.id),
            new_values={
                "order_type": order_type.value,
                "item_count": len(order_items),
                "guest_session_id": str(guest_session_id),
            },
        )
        return order

    async def get_owned(self, order_id: uuid.UUID, employee_id: uuid.UUID) -> Order:
        order = await self.orders.get_by_id(order_id)
        if order is None or order.employee_id != employee_id:
            raise NotFoundError("Order not found")
        return order

    async def list_for_employee(self, employee_id: uuid.UUID) -> list[Order]:
        return await self.orders.list_for_employee(employee_id)

    async def list_for_guest_session(self, guest_session_id: uuid.UUID) -> list[Order]:
        return await self.orders.list_for_guest_session(guest_session_id)

    async def cancel(self, order_id: uuid.UUID, employee_id: uuid.UUID) -> Order:
        order = await self.get_owned(order_id, employee_id)
        if order.status not in CANCELLABLE_STATUSES:
            raise ValidationAppError(f"Order cannot be cancelled from status {order.status.value}")

        order.status = OrderStatus.CANCELLED
        await self.orders.flush()

        await self.audit.record(
            action="order.cancelled",
            entity_type="order",
            entity_id=str(order.id),
            actor_employee_id=employee_id,
        )
        return order
