import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ConsumptionStatus, enum_column


class ConsumptionRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One row per OrderItem, created when its order is marked SERVED.
    `served_quantity` is the billable quantity (CLAUDE.md: "served
    quantity, not merely ordered quantity, determines consumption
    billing"). A correction is a two-step request/validate flow
    (docs/consumption.md): the employee's request sits in
    `requested_quantity` until a server approves it into `served_quantity`
    (or rejects it, leaving `served_quantity` untouched) -- never edited
    directly. `billed_entry_id` links to the LedgerEntry created when this
    record was first billed, so a later correction can reverse exactly
    that entry rather than guessing which one to reverse."""

    __tablename__ = "consumption_records"
    __table_args__ = (
        CheckConstraint("served_quantity >= 0", name="ck_consumption_served_qty_non_negative"),
    )

    order_item_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("order_items.id"), unique=True, nullable=False
    )
    served_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ConsumptionStatus] = mapped_column(
        enum_column(ConsumptionStatus, "consumption_status"),
        default=ConsumptionStatus.VALIDATED,
        nullable=False,
    )

    served_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    validated_by_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )
    validated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    requested_quantity: Mapped[int | None] = mapped_column(Integer)
    requested_reason: Mapped[str | None] = mapped_column(String(500))
    requested_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("employees.id")
    )
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    billed_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ledger_entries.id")
    )
