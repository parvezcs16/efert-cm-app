import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class SalesSummaryResponse(BaseModel):
    location_id: uuid.UUID
    since: datetime
    until: datetime
    total_orders: int
    orders_by_status: dict[str, int]
    orders_by_type: dict[str, int]
    total_revenue: Decimal


class ReconciliationLineRead(BaseModel):
    order_id: uuid.UUID
    order_number: str
    order_item_id: uuid.UUID
    menu_item_id: uuid.UUID
    ordered_quantity: int
    served_quantity: int
    expected_amount: Decimal
    billed_amount: Decimal
    matches: bool


class ReconciliationResponse(BaseModel):
    location_id: uuid.UUID
    since: datetime
    until: datetime
    lines: list[ReconciliationLineRead]
    mismatch_count: int


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_employee_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: str | None
    old_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    created_at: datetime
