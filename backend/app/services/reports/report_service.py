import uuid
from collections import Counter
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import OrderStatus
from app.repositories.billing_repository import LedgerEntryRepository
from app.repositories.consumption_repository import ConsumptionRecordRepository
from app.repositories.order_repository import OrderRepository


class SalesSummary:
    def __init__(
        self,
        *,
        total_orders: int,
        orders_by_status: dict[str, int],
        orders_by_type: dict[str, int],
        total_revenue: Decimal,
    ) -> None:
        self.total_orders = total_orders
        self.orders_by_status = orders_by_status
        self.orders_by_type = orders_by_type
        self.total_revenue = total_revenue


class ReconciliationLine:
    def __init__(
        self,
        *,
        order_id: uuid.UUID,
        order_number: str,
        order_item_id: uuid.UUID,
        menu_item_id: uuid.UUID,
        ordered_quantity: int,
        served_quantity: int,
        expected_amount: Decimal,
        billed_amount: Decimal,
    ) -> None:
        self.order_id = order_id
        self.order_number = order_number
        self.order_item_id = order_item_id
        self.menu_item_id = menu_item_id
        self.ordered_quantity = ordered_quantity
        self.served_quantity = served_quantity
        self.expected_amount = expected_amount
        self.billed_amount = billed_amount
        self.matches = expected_amount == billed_amount


class ReportService:
    """Management reporting (requirements.md: "Review reports and audit
    logs"). Computed on demand from orders/consumption/ledger data, not
    cached -- report volumes here don't warrant it yet."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.orders = OrderRepository(db)
        self.consumption = ConsumptionRecordRepository(db)
        self.ledger_entries = LedgerEntryRepository(db)

    async def sales_summary(
        self, location_id: uuid.UUID, *, since: datetime, until: datetime
    ) -> SalesSummary:
        orders = await self.orders.list_for_location_in_period(
            location_id, since=since, until=until
        )
        served_orders = [o for o in orders if o.status == OrderStatus.SERVED]
        item_ids = [item.id for order in served_orders for item in order.items]
        consumption_map = await self.consumption.list_by_order_items(item_ids)

        total_revenue = sum(
            (
                item.unit_price * consumption_map[item.id].served_quantity
                for order in served_orders
                for item in order.items
                if item.id in consumption_map
            ),
            Decimal("0"),
        )

        return SalesSummary(
            total_orders=len(orders),
            orders_by_status=dict(Counter(o.status.value for o in orders)),
            orders_by_type=dict(Counter(o.order_type.value for o in orders)),
            total_revenue=total_revenue,
        )

    async def reconciliation(
        self, location_id: uuid.UUID, *, since: datetime, until: datetime
    ) -> list[ReconciliationLine]:
        """For every served item: does the billed amount (net of any
        corrections) match served_quantity * unit_price? A mismatch would
        indicate a bug or manual data tampering -- normal operation should
        never produce one, since ConsumptionService/LedgerService always
        keep them in lockstep."""
        orders = await self.orders.list_for_location_in_period(
            location_id, since=since, until=until
        )
        served_orders = [o for o in orders if o.status == OrderStatus.SERVED]
        item_ids = [item.id for order in served_orders for item in order.items]
        consumption_map = await self.consumption.list_by_order_items(item_ids)
        billed_map = await self.ledger_entries.net_amount_by_source_id(item_ids)

        lines = []
        for order in served_orders:
            for item in order.items:
                record = consumption_map.get(item.id)
                if record is None:
                    continue
                lines.append(
                    ReconciliationLine(
                        order_id=order.id,
                        order_number=order.order_number,
                        order_item_id=item.id,
                        menu_item_id=item.menu_item_id,
                        ordered_quantity=item.ordered_quantity,
                        served_quantity=record.served_quantity,
                        expected_amount=item.unit_price * record.served_quantity,
                        billed_amount=billed_map.get(item.id, Decimal("0")),
                    )
                )
        return lines
