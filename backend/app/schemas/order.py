import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import CustomerType, IngredientStatus, OrderStatus, OrderType


class OrderItemCreateRequest(BaseModel):
    menu_item_id: uuid.UUID
    quantity: int = Field(gt=0, le=50)


class OrderCreateRequest(BaseModel):
    location_id: uuid.UUID
    order_type: OrderType
    scheduled_for: datetime | None = None
    items: list[OrderItemCreateRequest] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_scheduling(self) -> "OrderCreateRequest":
        if self.order_type == OrderType.BOOK_FOR_LATER:
            if self.scheduled_for is None:
                raise ValueError("scheduled_for is required for BOOK_FOR_LATER orders")
        elif self.scheduled_for is not None:
            raise ValueError("scheduled_for is only valid for BOOK_FOR_LATER orders")
        return self


class OrderItemRead(BaseModel):
    """Deliberately excludes unit_price: employees don't see pricing in the
    ordering UX (CLAUDE.md). Their charges surface later via the mess
    ledger (Phase 8)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    menu_item_id: uuid.UUID
    ordered_quantity: int
    kitchen_station_id: uuid.UUID | None
    # Filled in by endpoints that look names up; not an ORM attribute.
    menu_item_name: str | None = None


class OrderItemUpdate(BaseModel):
    order_item_id: uuid.UUID
    quantity: int = Field(gt=0, le=50)


class OrderItemsUpdateRequest(BaseModel):
    """The items to keep, with their (possibly reduced) quantities. Items
    of the order that are omitted are removed."""

    items: list[OrderItemUpdate] = Field(min_length=1)


class QueueOrderRequest(BaseModel):
    """Maps order_item_id -> kitchen_station_id. Every item on the order
    must be assigned (docs/kitchen.md: "Order items may be routed to
    different stations")."""

    station_assignments: dict[uuid.UUID, uuid.UUID] = Field(min_length=1)


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_number: str
    location_id: uuid.UUID
    customer_type: CustomerType
    order_type: OrderType
    scheduled_for: datetime | None
    status: OrderStatus
    ingredient_status: IngredientStatus | None
    ingredient_response_message: str | None
    created_at: datetime
    items: list[OrderItemRead]


class KitchenBoardItemRead(BaseModel):
    """Display-only view of an order item for the kitchen big screen:
    the item name instead of an ID, and no unit_price."""

    menu_item_name: str
    quantity: int
    kitchen_station_id: uuid.UUID | None
    kitchen_station_name: str | None


class KitchenBoardOrderRead(BaseModel):
    id: uuid.UUID
    order_number: str
    customer_type: CustomerType
    order_type: OrderType
    status: OrderStatus
    scheduled_for: datetime | None
    created_at: datetime
    # Last status change, used by the board for "time in this column".
    updated_at: datetime
    items: list[KitchenBoardItemRead]
