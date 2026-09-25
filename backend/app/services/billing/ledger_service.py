import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import LedgerAccount, LedgerEntry
from app.models.consumption import ConsumptionRecord
from app.models.enums import (
    GuestType,
    LedgerAccountType,
    LedgerEntryType,
    LedgerSourceType,
)
from app.models.order import Order, OrderItem
from app.repositories.billing_repository import LedgerAccountRepository, LedgerEntryRepository
from app.repositories.guest_repository import GuestRepository, GuestSessionRepository


class LedgerService:
    """Posts charges/adjustments from validated consumption. Never mutates
    an existing LedgerEntry -- every call here only ever INSERTs (CLAUDE.md
    "never delete financial transactions", "corrections... use
    reversal/adjustment entries")."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.accounts = LedgerAccountRepository(db)
        self.entries = LedgerEntryRepository(db)
        self.guests = GuestRepository(db)
        self.guest_sessions = GuestSessionRepository(db)

    async def get_or_create_employee_account(self, employee_id: uuid.UUID) -> LedgerAccount:
        account = await self.accounts.get_by_employee(employee_id)
        if account is None:
            account = LedgerAccount(
                account_type=LedgerAccountType.EMPLOYEE_PERSONAL, employee_id=employee_id
            )
            self.accounts.add(account)
            await self.accounts.flush()
        return account

    async def get_or_create_official_account(self, location_id: uuid.UUID) -> LedgerAccount:
        account = await self.accounts.get_by_location(location_id)
        if account is None:
            account = LedgerAccount(
                account_type=LedgerAccountType.OFFICIAL, location_id=location_id
            )
            self.accounts.add(account)
            await self.accounts.flush()
        return account

    async def _resolve_billing_target(
        self, order: Order
    ) -> tuple[LedgerAccount, LedgerSourceType, uuid.UUID | None]:
        """Returns (account, source_type, guest_session_id_for_reference)."""
        if order.customer_type.value == "EMPLOYEE":
            assert order.employee_id is not None
            account = await self.get_or_create_employee_account(order.employee_id)
            return account, LedgerSourceType.PERSONAL_CONSUMPTION, None

        assert order.guest_session_id is not None
        session = await self.guest_sessions.get_by_id(order.guest_session_id)
        assert session is not None
        guest = await self.guests.get_by_id(session.guest_id)
        assert guest is not None

        if guest.guest_type == GuestType.PRIVATE:
            # "Post to host employee's ledger" (docs/billing.md) -- the
            # session's host, who may differ from the guest's original
            # registering host (see Phase 6 notes).
            account = await self.get_or_create_employee_account(session.host_employee_id)
            return account, LedgerSourceType.PRIVATE_GUEST, session.id

        account = await self.get_or_create_official_account(order.location_id)
        return account, LedgerSourceType.OFFICIAL_GUEST, session.id

    async def post_consumption_charge(
        self,
        *,
        order: Order,
        order_item: OrderItem,
        consumption_record: ConsumptionRecord,
        actor_id: uuid.UUID,
    ) -> LedgerEntry | None:
        """"Only validated served consumption creates the normal food
        charge" (docs/billing.md). Called once, when an order is served."""
        if consumption_record.served_quantity == 0:
            return None

        account, source_type, guest_session_id = await self._resolve_billing_target(order)
        amount = order_item.unit_price * consumption_record.served_quantity

        entry = LedgerEntry(
            ledger_account_id=account.id,
            source_type=source_type,
            source_id=order_item.id,
            guest_session_id=guest_session_id,
            entry_type=LedgerEntryType.DEBIT,
            amount=amount,
            reason=f"Order {order.order_number} served ({consumption_record.served_quantity}x)",
            created_by_id=actor_id,
        )
        self.entries.add(entry)
        await self.entries.flush()

        consumption_record.billed_entry_id = entry.id
        return entry

    async def post_correction_adjustment(
        self,
        *,
        order: Order,
        order_item: OrderItem,
        consumption_record: ConsumptionRecord,
        old_quantity: int,
        new_quantity: int,
        actor_id: uuid.UUID,
    ) -> LedgerEntry | None:
        """A single net adjustment entry for the quantity delta, referencing
        the original charge via reversal_of_id -- not a reversal+recharge
        pair, to keep the ledger minimal while still never touching the
        original entry (docs/consumption.md "Returned Food")."""
        delta = old_quantity - new_quantity
        if delta == 0:
            return None

        account, source_type, guest_session_id = await self._resolve_billing_target(order)
        amount: Decimal = order_item.unit_price * abs(delta)
        entry_type = LedgerEntryType.CREDIT if delta > 0 else LedgerEntryType.DEBIT
        direction = "reduced" if delta > 0 else "increased"

        entry = LedgerEntry(
            ledger_account_id=account.id,
            source_type=source_type,
            source_id=order_item.id,
            guest_session_id=guest_session_id,
            entry_type=entry_type,
            amount=amount,
            reason=(
                f"Correction on order {order.order_number}: served quantity {direction} "
                f"from {old_quantity} to {new_quantity}"
            ),
            reversal_of_id=consumption_record.billed_entry_id,
            created_by_id=actor_id,
        )
        self.entries.add(entry)
        await self.entries.flush()
        return entry

    async def post_manual_adjustment(
        self,
        *,
        ledger_account_id: uuid.UUID,
        source_type: LedgerSourceType,
        entry_type: LedgerEntryType,
        amount: Decimal,
        reason: str,
        actor_id: uuid.UUID,
        reversal_of_id: uuid.UUID | None = None,
    ) -> LedgerEntry:
        """Ad hoc management adjustment (requirements.md: "Adjust/reverse
        billing") -- e.g. a goodwill credit or correcting an error outside
        the normal served-quantity-correction flow. Always an explicit
        actor + reason; never touches an existing entry."""
        entry = LedgerEntry(
            ledger_account_id=ledger_account_id,
            source_type=source_type,
            entry_type=entry_type,
            amount=amount,
            reason=reason,
            reversal_of_id=reversal_of_id,
            created_by_id=actor_id,
        )
        self.entries.add(entry)
        await self.entries.flush()
        return entry

    async def statement(
        self,
        ledger_account_id: uuid.UUID,
        *,
        source_types: list[LedgerSourceType] | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[LedgerEntry]:
        return await self.entries.list_for_account(
            ledger_account_id, source_types=source_types, since=since, until=until
        )
