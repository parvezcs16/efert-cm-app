import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    ActiveStatus,
    LedgerAccountType,
    LedgerEntryType,
    LedgerSourceType,
    enum_column,
)


class LedgerAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Exactly one of employee_id/location_id is set, matching
    account_type -- one EMPLOYEE_PERSONAL account per employee (global,
    not per-location, since employees may order from any location), one
    OFFICIAL account per location (docs/billing.md "Accounts")."""

    __tablename__ = "ledger_accounts"
    __table_args__ = (
        UniqueConstraint("employee_id", name="uq_ledger_account_employee"),
        UniqueConstraint("location_id", name="uq_ledger_account_location"),
    )

    account_type: Mapped[LedgerAccountType] = mapped_column(
        enum_column(LedgerAccountType, "ledger_account_type"), nullable=False
    )
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("employees.id")
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("locations.id")
    )
    status: Mapped[ActiveStatus] = mapped_column(
        enum_column(ActiveStatus, "ledger_account_status"),
        default=ActiveStatus.ACTIVE,
        nullable=False,
    )


class LedgerEntry(UUIDPrimaryKeyMixin, Base):
    """Append-only by convention: no service ever UPDATEs or DELETEs a row
    here (CLAUDE.md "never delete financial transactions" /
    "corrections... use reversal/adjustment entries"). No TimestampMixin
    (no updated_at) -- a ledger entry is never modified after creation."""

    __tablename__ = "ledger_entries"

    ledger_account_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ledger_accounts.id"), nullable=False, index=True
    )
    source_type: Mapped[LedgerSourceType] = mapped_column(
        enum_column(LedgerSourceType, "ledger_source_type"), nullable=False
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True))
    # Traces a PRIVATE_GUEST/OFFICIAL_GUEST entry back to the guest visit
    # for reporting (docs/guest-management.md "preserve guest identity").
    guest_session_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("guest_sessions.id")
    )

    entry_type: Mapped[LedgerEntryType] = mapped_column(
        enum_column(LedgerEntryType, "ledger_entry_type"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)

    reversal_of_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ledger_entries.id")
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("employees.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
