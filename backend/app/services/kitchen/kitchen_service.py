import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.enums import ActiveStatus, IngredientStatus, OrderStatus, OrderType
from app.models.order import Order
from app.repositories.location_repository import KitchenStationRepository
from app.repositories.menu_repository import MenuItemRepository
from app.repositories.order_repository import OrderRepository
from app.schemas.order import KitchenBoardItemRead, KitchenBoardOrderRead
from app.services.audit_service import AuditService
from app.services.consumption.consumption_service import ConsumptionService
from app.websocket.manager import kitchen_ws_manager

# "Cancellation is permitted before serving" already covers CANCELLED
# (OrderService owns that transition); these are the kitchen-execution
# steps this service owns.
NON_TERMINAL_STATUSES = {
    OrderStatus.PENDING,
    OrderStatus.CONFIRMED,
    OrderStatus.QUEUED,
    OrderStatus.PREPARING,
    OrderStatus.READY,
}

# Immediate orders outrank released/booked orders; FIFO within each group
# (docs/kitchen.md "Queue"). Ingredient-confirmation gating for booked
# orders before they may be queued is Phase 7 -- not enforced here yet.
_PRIORITY_RANK = {OrderType.DINE_IN: 0, OrderType.TAKEAWAY: 0, OrderType.BOOK_FOR_LATER: 1}

# Everything the kitchen big screen shows: from "just placed" through
# "waiting at the pass". SERVED/CANCELLED drop off the board.
BOARD_STATUSES = [
    OrderStatus.PENDING,
    OrderStatus.CONFIRMED,
    OrderStatus.QUEUED,
    OrderStatus.PREPARING,
    OrderStatus.READY,
]


class KitchenService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.orders = OrderRepository(db)
        self.stations = KitchenStationRepository(db)
        self.audit = AuditService(db)

    async def _get_order(self, order_id: uuid.UUID) -> Order:
        order = await self.orders.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order not found")
        return order

    async def _transition(
        self,
        order_id: uuid.UUID,
        actor_id: uuid.UUID,
        *,
        expected: OrderStatus,
        target: OrderStatus,
    ) -> Order:
        order = await self._get_order(order_id)
        if order.status != expected:
            raise ValidationAppError(
                f"Order must be {expected.value} to move to {target.value} "
                f"(currently {order.status.value})"
            )
        order.status = target
        await self.orders.flush()
        if target == OrderStatus.SERVED:
            await ConsumptionService(self.db).create_records_for_served_order(order, actor_id)
        await self._record_and_broadcast(order, actor_id)
        return order

    async def confirm(self, order_id: uuid.UUID, actor_id: uuid.UUID) -> Order:
        order = await self._get_order(order_id)
        if (
            order.order_type == OrderType.BOOK_FOR_LATER
            and order.ingredient_status != IngredientStatus.CONFIRMED
        ):
            raise ValidationAppError(
                "Booked order ingredients must be confirmed before the order can proceed "
                "(see /orders/{id}/booking/confirm-ingredients)"
            )
        return await self._transition(
            order_id, actor_id, expected=OrderStatus.PENDING, target=OrderStatus.CONFIRMED
        )

    async def queue(
        self,
        order_id: uuid.UUID,
        actor_id: uuid.UUID,
        station_assignments: dict[uuid.UUID, uuid.UUID],
    ) -> Order:
        order = await self._get_order(order_id)
        if order.status != OrderStatus.CONFIRMED:
            raise ValidationAppError(
                f"Order must be CONFIRMED to be queued (currently {order.status.value})"
            )

        item_ids = {item.id for item in order.items}
        if set(station_assignments) != item_ids:
            raise ValidationAppError("Every order item must be assigned a kitchen station")

        stations = await self.stations.list_for_location(order.location_id)
        valid_station_ids = {s.id for s in stations if s.status == ActiveStatus.ACTIVE}
        for station_id in station_assignments.values():
            if station_id not in valid_station_ids:
                raise ValidationAppError("Kitchen station does not belong to this location")

        for item in order.items:
            item.kitchen_station_id = station_assignments[item.id]

        order.status = OrderStatus.QUEUED
        await self.orders.flush()
        await self._record_and_broadcast(order, actor_id)
        return order

    async def start_preparing(self, order_id: uuid.UUID, actor_id: uuid.UUID) -> Order:
        return await self._transition(
            order_id, actor_id, expected=OrderStatus.QUEUED, target=OrderStatus.PREPARING
        )

    async def mark_ready(self, order_id: uuid.UUID, actor_id: uuid.UUID) -> Order:
        return await self._transition(
            order_id, actor_id, expected=OrderStatus.PREPARING, target=OrderStatus.READY
        )

    async def serve(self, order_id: uuid.UUID, actor_id: uuid.UUID) -> Order:
        return await self._transition(
            order_id, actor_id, expected=OrderStatus.READY, target=OrderStatus.SERVED
        )

    async def serve_directly(self, order_id: uuid.UUID, actor_id: uuid.UUID) -> Order:
        """"A server may mark an order served when food is actually handed
        over" -- bypasses the intermediate kitchen steps entirely."""
        order = await self._get_order(order_id)
        if order.status not in NON_TERMINAL_STATUSES:
            raise ValidationAppError(f"Order cannot be served from status {order.status.value}")

        order.status = OrderStatus.SERVED
        await self.orders.flush()
        await ConsumptionService(self.db).create_records_for_served_order(order, actor_id)
        await self._record_and_broadcast(order, actor_id, action="order.served_directly")
        return order

    async def get_incoming_orders(self, location_id: uuid.UUID) -> list[Order]:
        """Orders needing a confirm/queue action, not yet tied to a
        station -- station queues (get_station_queue) only cover
        QUEUED/PREPARING. A BOOK_FOR_LATER order whose ingredients aren't
        confirmed yet is excluded here (it would just reject the confirm
        action); it shows up in the pending-bookings list instead."""
        orders = await self.orders.list_for_location_by_status(
            location_id, [OrderStatus.PENDING, OrderStatus.CONFIRMED]
        )
        return [
            o
            for o in orders
            if o.order_type != OrderType.BOOK_FOR_LATER
            or o.ingredient_status == IngredientStatus.CONFIRMED
        ]

    async def get_station_queue(self, location_id: uuid.UUID, station_id: uuid.UUID) -> list[Order]:
        orders = await self.orders.list_for_location_by_status(
            location_id, [OrderStatus.QUEUED, OrderStatus.PREPARING]
        )
        at_station = [
            o for o in orders if any(item.kitchen_station_id == station_id for item in o.items)
        ]
        return sorted(at_station, key=lambda o: (_PRIORITY_RANK[o.order_type], o.created_at))

    async def get_board(
        self, location_id: uuid.UUID, station_id: uuid.UUID | None = None
    ) -> list[KitchenBoardOrderRead]:
        """Read-only snapshot for the kitchen display screen. Booked orders
        whose ingredients aren't confirmed yet are left off (nothing to cook
        until management signs them off). With a station filter, only
        orders routed to that station appear, showing only its items --
        orders not yet queued to any station are therefore hidden."""
        orders = await self.orders.list_for_location_by_status(location_id, BOARD_STATUSES)
        orders = [
            o
            for o in orders
            if o.order_type != OrderType.BOOK_FOR_LATER
            or o.ingredient_status == IngredientStatus.CONFIRMED
        ]

        stations = await self.stations.list_for_location(location_id)
        station_names = {s.id: s.name for s in stations}
        item_names = await MenuItemRepository(self.db).get_names(
            {item.menu_item_id for o in orders for item in o.items}
        )

        board: list[KitchenBoardOrderRead] = []
        for order in sorted(orders, key=lambda o: (_PRIORITY_RANK[o.order_type], o.created_at)):
            items = [
                item
                for item in order.items
                if station_id is None or item.kitchen_station_id == station_id
            ]
            if not items:
                continue
            board.append(
                KitchenBoardOrderRead(
                    id=order.id,
                    order_number=order.order_number,
                    customer_type=order.customer_type,
                    order_type=order.order_type,
                    status=order.status,
                    scheduled_for=order.scheduled_for,
                    created_at=order.created_at,
                    updated_at=order.updated_at,
                    items=[
                        KitchenBoardItemRead(
                            menu_item_name=item_names.get(item.menu_item_id, "Unknown item"),
                            quantity=item.ordered_quantity,
                            kitchen_station_id=item.kitchen_station_id,
                            kitchen_station_name=station_names.get(item.kitchen_station_id)
                            if item.kitchen_station_id
                            else None,
                        )
                        for item in items
                    ],
                )
            )
        return board

    async def _record_and_broadcast(
        self, order: Order, actor_id: uuid.UUID, *, action: str | None = None
    ) -> None:
        await self.audit.record(
            action=action or "order.status_changed",
            entity_type="order",
            entity_id=str(order.id),
            actor_employee_id=actor_id,
            new_values={"status": order.status.value},
        )
        await kitchen_ws_manager.broadcast(
            order.location_id,
            {
                "type": "order.status_changed",
                "order_id": str(order.id),
                "order_number": order.order_number,
                "status": order.status.value,
            },
        )
