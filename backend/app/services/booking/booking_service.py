import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.enums import CustomerType, IngredientStatus, OrderType
from app.models.order import Order
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.guest_repository import GuestSessionRepository
from app.repositories.order_repository import OrderRepository
from app.services.audit_service import AuditService
from app.services.notifications.dispatch_service import NotificationDispatchService
from app.websocket.manager import kitchen_ws_manager


class BookingService:
    """Ingredient confirmation for BOOK_FOR_LATER orders (docs/kitchen.md
    "Booked Orders", docs/business-rules.md "Booked Orders"). Confirming
    here is what unblocks KitchenService.confirm() for a booked order."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.orders = OrderRepository(db)
        self.employees = EmployeeRepository(db)
        self.guest_sessions = GuestSessionRepository(db)
        self.audit = AuditService(db)
        self.notifier = NotificationDispatchService(db)

    async def _get_pending_booking(self, order_id: uuid.UUID) -> Order:
        order = await self.orders.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order not found")
        if order.order_type != OrderType.BOOK_FOR_LATER:
            raise ValidationAppError("Only BOOK_FOR_LATER orders require ingredient confirmation")
        if order.ingredient_status not in (IngredientStatus.PENDING, IngredientStatus.DELAYED):
            raise ValidationAppError(
                f"Order ingredients are already {order.ingredient_status.value}"
                if order.ingredient_status
                else "Order has no pending ingredient review"
            )
        return order

    async def _notify_customer(
        self, order: Order, subject: str, body: str, *, notification_type: str
    ) -> None:
        """Guests have no account/email (docs/database.md's Guest entity
        has none), so a guest booking's update goes to that session's host
        employee instead."""
        employee = None
        if order.customer_type == CustomerType.EMPLOYEE and order.employee_id is not None:
            employee = await self.employees.get_by_id(order.employee_id)
        elif order.customer_type == CustomerType.GUEST and order.guest_session_id is not None:
            session = await self.guest_sessions.get_by_id(order.guest_session_id)
            if session is not None:
                employee = await self.employees.get_by_id(session.host_employee_id)

        if employee is not None:
            await self.notifier.send_email(
                to=employee.email,
                subject=subject,
                body=body,
                type=notification_type,
                payload_reference=str(order.id),
            )

    async def confirm_ingredients(self, order_id: uuid.UUID, actor_id: uuid.UUID) -> Order:
        order = await self._get_pending_booking(order_id)

        order.ingredient_status = IngredientStatus.CONFIRMED
        order.ingredient_reviewed_by_id = actor_id
        order.ingredient_reviewed_at = datetime.now(UTC)
        order.ingredient_response_message = None
        await self.orders.flush()

        await self.audit.record(
            action="booking.ingredients_confirmed",
            entity_type="order",
            entity_id=str(order.id),
            actor_employee_id=actor_id,
        )
        await self._notify_customer(
            order,
            "Your booked order is confirmed",
            f"Order {order.order_number} is confirmed for {order.scheduled_for}.",
            notification_type="BOOKING_CONFIRMED",
        )
        await kitchen_ws_manager.broadcast(
            order.location_id,
            {
                "type": "booking.ingredients_confirmed",
                "order_id": str(order.id),
                "order_number": order.order_number,
            },
        )
        return order

    async def delay_ingredients(
        self,
        order_id: uuid.UUID,
        actor_id: uuid.UUID,
        *,
        new_scheduled_for: datetime,
        reason: str,
    ) -> Order:
        order = await self._get_pending_booking(order_id)
        if new_scheduled_for <= datetime.now(UTC):
            raise ValidationAppError("new_scheduled_for must be in the future")

        order.ingredient_status = IngredientStatus.DELAYED
        order.ingredient_reviewed_by_id = actor_id
        order.ingredient_reviewed_at = datetime.now(UTC)
        order.ingredient_response_message = reason
        order.scheduled_for = new_scheduled_for
        await self.orders.flush()

        await self.audit.record(
            action="booking.ingredients_delayed",
            entity_type="order",
            entity_id=str(order.id),
            actor_employee_id=actor_id,
            new_values={"new_scheduled_for": new_scheduled_for.isoformat(), "reason": reason},
        )
        await self._notify_customer(
            order,
            "Your booked order has been delayed",
            f"Order {order.order_number} is delayed to {new_scheduled_for}. Reason: {reason}",
            notification_type="BOOKING_DELAYED",
        )
        await kitchen_ws_manager.broadcast(
            order.location_id,
            {
                "type": "booking.ingredients_delayed",
                "order_id": str(order.id),
                "order_number": order.order_number,
                "scheduled_for": new_scheduled_for.isoformat(),
            },
        )
        return order
