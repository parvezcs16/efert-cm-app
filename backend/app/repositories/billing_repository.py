import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import LedgerAccount, LedgerEntry
from app.models.enums import LedgerAccountType, LedgerEntryType, LedgerSourceType


class LedgerAccountRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_employee(self, employee_id: uuid.UUID) -> LedgerAccount | None:
        result = await self.db.execute(
            select(LedgerAccount).where(
                LedgerAccount.account_type == LedgerAccountType.EMPLOYEE_PERSONAL,
                LedgerAccount.employee_id == employee_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_location(self, location_id: uuid.UUID) -> LedgerAccount | None:
        result = await self.db.execute(
            select(LedgerAccount).where(
                LedgerAccount.account_type == LedgerAccountType.OFFICIAL,
                LedgerAccount.location_id == location_id,
            )
        )
        return result.scalar_one_or_none()

    def add(self, account: LedgerAccount) -> None:
        self.db.add(account)

    async def flush(self) -> None:
        await self.db.flush()


class LedgerEntryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, entry: LedgerEntry) -> None:
        self.db.add(entry)

    async def flush(self) -> None:
        await self.db.flush()

    async def list_for_account(
        self,
        ledger_account_id: uuid.UUID,
        *,
        source_types: list[LedgerSourceType] | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[LedgerEntry]:
        query = select(LedgerEntry).where(LedgerEntry.ledger_account_id == ledger_account_id)
        if source_types is not None:
            query = query.where(LedgerEntry.source_type.in_(source_types))
        if since is not None:
            query = query.where(LedgerEntry.created_at >= since)
        if until is not None:
            query = query.where(LedgerEntry.created_at <= until)
        result = await self.db.execute(query.order_by(LedgerEntry.created_at))
        return list(result.scalars().all())

    async def net_amount_by_source_id(
        self, source_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, Decimal]:
        """DEBIT-minus-CREDIT net billed amount per source_id (an
        order_item_id in practice) -- used by the reconciliation report to
        compare what was actually billed against what should have been."""
        if not source_ids:
            return {}

        signed_amount = case(
            (LedgerEntry.entry_type == LedgerEntryType.DEBIT, LedgerEntry.amount),
            else_=-LedgerEntry.amount,
        )
        result = await self.db.execute(
            select(LedgerEntry.source_id, func.sum(signed_amount))
            .where(LedgerEntry.source_id.in_(source_ids))
            .group_by(LedgerEntry.source_id)
        )
        return {row[0]: row[1] for row in result.all()}
