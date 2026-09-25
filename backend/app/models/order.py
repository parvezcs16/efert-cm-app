import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, Sequence, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import CustomerType, IngredientStatus, OrderStatus, OrderType, enum_column

# Registered on Base.metadata (rather than only created ad hoc in the
# migration) so both `alembic upgrade` and a test suite's
# `Base.metadata.create_all` provision it. Used via raw `nextval()` in
# OrderRepository rather than as a column server_default.
order_number_seq = Sequence("order_number_seq", start=1, metadata=Base.metadata)


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Employee and guest orders share this table but "remain separate"
    (docs/ordering.md) via the CHECK constraint below: exactly one of
    employee_id/guest_session_id is set, matching customer_type."""

    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            "(customer_type = 'EMPLOYEE' AND employee_id IS NOT NULL"
            " AND guest_session_id IS NULL)"
            " OR (customer_type = 'GUEST' AND guest_session_id IS NOT NULL"
            " AND employee_id IS NULL)",
            name="ck_order_customer_type_consistency",
        ),
    )

    order_number: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    location_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("locations.id"), nullable=False, index=True
    )
    customer_type: Mapped[CustomerType] = mapped_column(
        enum_column(CustomerType, "customer_type"), nullable=False
    )
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("employees.id"), index=True
    )
    guest_session_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("guest_sessions.id"), index=True
    )
    order_type: Mapped[OrderType] = mapped_column(
        enum_column(OrderType, "order_type"), nullable=False
    )
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[OrderStatus] = mapped_column(
        enum_column(OrderStatus, "order_status"), default=OrderStatus.PENDING, nullable=False
    )

    # Booked-order ingredient confirmation (Phase 7). Null for
    # DINE_IN/TAKEAWAY orders, where it doesn't apply.
    ingredient_status: Mapped[IngredientStatus | None] = mapped_column(
        enum_column(IngredientStatus, "ingredient_status")
    )
    ingredient_reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("employees.id")
    )
    ingredient_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ingredient_response_message: Mapped[str | None] = mapped_column(String(500))

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """`kitchen_station_id` is deliberately nullable and unset by Phase 4:
    routing an item to a station is a kitchen-queue concern owned by Phase
    5. `unit_price` is a snapshot taken from MenuItemLocation at order time
    -- the immutable historical record CLAUDE.md requires; it does not
    change if the location's price later changes."""

    __tablename__ = "order_items"
    __table_args__ = (CheckConstraint("ordered_quantity > 0", name="ck_order_item_qty_positive"),)

    order_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True
    )
    menu_item_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("menu_items.id"), nullable=False
    )
    kitchen_station_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("kitchen_stations.id")
    )
    ordered_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
