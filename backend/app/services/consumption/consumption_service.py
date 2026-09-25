import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationAppError
from app.models.consumption import ConsumptionRecord
from app.models.enums import ConsumptionStatus
from app.models.order import Order
from app.repositories.consumption_repository import ConsumptionRecordRepository
from app.repositories.order_repository import OrderRepository
from app.services.audit_service import AuditService
from app.services.billing.ledger_service import LedgerService


class ConsumptionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.orders = OrderRepository(db)
        self.consumption = ConsumptionRecordRepository(db)
        self.ledger = LedgerService(db)
        self.audit = AuditService(db)

    async def create_records_for_served_order(self, order: Order, actor_id: uuid.UUID) -> None:
        """"Consumption represents food actually served" (docs/consumption.md).
        Called once when an order transitions to SERVED; defaults served
        quantity to ordered quantity -- the server marking it served is
        implicitly attesting the full order was handed over. A shortfall is
        handled afterwards via the correction request/validate flow, not by
        guessing a different default here."""
        now = datetime.now(UTC)
        for item in order.items:
            record = ConsumptionRecord(
                order_item_id=item.id,
                served_quantity=item.ordered_quantity,
                status=ConsumptionStatus.VALIDATED,
                served_at=now,
                validated_by_id=actor_id,
                validated_at=now,
            )
            self.consumption.add(record)
            await self.consumption.flush()

            await self.ledger.post_consumption_charge(
                order=order, order_item=item, consumption_record=record, actor_id=actor_id
            )

        await self.audit.record(
            action="consumption.recorded",
            entity_type="order",
            entity_id=str(order.id),
            actor_employee_id=actor_id,
            new_values={"item_count": len(order.items)},
        )

    async def _get_order_and_item(
        self, order_id: uuid.UUID, order_item_id: uuid.UUID
    ) -> tuple[Order, ConsumptionRecord]:
        order = await self.orders.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order not found")

        item = next((i for i in order.items if i.id == order_item_id), None)
        if item is None:
            raise NotFoundError("Order item not found")

        record = await self.consumption.get_by_order_item(order_item_id)
        if record is None:
            raise ValidationAppError("This item has not been served yet")

        return order, record

    async def request_correction(
        self,
        *,
        order_id: uuid.UUID,
        order_item_id: uuid.UUID,
        employee_id: uuid.UUID,
        requested_quantity: int,
        reason: str,
    ) -> ConsumptionRecord:
        order, record = await self._get_order_and_item(order_id, order_item_id)
        if order.employee_id != employee_id:
            raise NotFoundError("Order not found")
        if record.status != ConsumptionStatus.VALIDATED:
            raise ValidationAppError("A correction is already pending for this item")

        item = next(i for i in order.items if i.id == order_item_id)
        if not (0 <= requested_quantity <= item.ordered_quantity):
            raise ValidationAppError(
                f"requested_quantity must be between 0 and {item.ordered_quantity}"
            )

        record.status = ConsumptionStatus.CORRECTION_REQUESTED
        record.requested_quantity = requested_quantity
        record.requested_reason = reason
        record.requested_by_id = employee_id
        record.requested_at = datetime.now(UTC)
        await self.consumption.flush()

        await self.audit.record(
            action="consumption.correction_requested",
            entity_type="consumption_record",
            entity_id=str(record.id),
            actor_employee_id=employee_id,
            old_values={"served_quantity": record.served_quantity},
            new_values={"requested_quantity": requested_quantity, "reason": reason},
        )
        return record

    async def validate_correction(
        self,
        *,
        order_id: uuid.UUID,
        order_item_id: uuid.UUID,
        actor_id: uuid.UUID,
        approve: bool,
    ) -> ConsumptionRecord:
        order, record = await self._get_order_and_item(order_id, order_item_id)
        if record.status != ConsumptionStatus.CORRECTION_REQUESTED:
            raise ValidationAppError("No pending correction request for this item")
        if record.requested_quantity is None:
            raise ValidationAppError("No pending correction request for this item")

        item = next(i for i in order.items if i.id == order_item_id)
        old_quantity = record.served_quantity

        if approve:
            new_quantity = record.requested_quantity
            record.served_quantity = new_quantity
            await self.ledger.post_correction_adjustment(
                order=order,
                order_item=item,
                consumption_record=record,
                old_quantity=old_quantity,
                new_quantity=new_quantity,
                actor_id=actor_id,
            )

        record.status = ConsumptionStatus.VALIDATED
        record.validated_by_id = actor_id
        record.validated_at = datetime.now(UTC)
        record.requested_quantity = None
        record.requested_reason = None
        record.requested_by_id = None
        record.requested_at = None
        await self.consumption.flush()

        action = (
            "consumption.correction_validated" if approve else "consumption.correction_rejected"
        )
        await self.audit.record(
            action=action,
            entity_type="consumption_record",
            entity_id=str(record.id),
            actor_employee_id=actor_id,
            old_values={"served_quantity": old_quantity},
            new_values={"served_quantity": record.served_quantity},
        )
        return record

    async def get_for_order_item(
        self, order_id: uuid.UUID, order_item_id: uuid.UUID, employee_id: uuid.UUID
    ) -> ConsumptionRecord:
        order, record = await self._get_order_and_item(order_id, order_item_id)
        if order.employee_id != employee_id:
            raise AuthorizationError("You do not have permission to view this record")
        return record
