import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import (
    get_current_employee,
    require_billing_admin,
    require_location_authority,
)
from app.core.database import get_db
from app.core.exceptions import ValidationAppError
from app.models.billing import LedgerEntry
from app.models.employee import Employee
from app.models.enums import LedgerEntryType, LedgerSourceType
from app.schemas.billing import (
    EmployeeAdjustmentRequest,
    LedgerEntryRead,
    OfficialAdjustmentRequest,
    StatementResponse,
)
from app.services.billing.ledger_service import LedgerService

router = APIRouter(prefix="/billing", tags=["billing"])


def _to_statement(entries: list[LedgerEntry]) -> StatementResponse:
    total_debit = sum(
        (e.amount for e in entries if e.entry_type == LedgerEntryType.DEBIT), Decimal("0")
    )
    total_credit = sum(
        (e.amount for e in entries if e.entry_type == LedgerEntryType.CREDIT), Decimal("0")
    )
    return StatementResponse(
        entries=[LedgerEntryRead.model_validate(e) for e in entries],
        total_debit=total_debit,
        total_credit=total_credit,
        net_balance=total_debit - total_credit,
    )


@router.get("/me/personal", response_model=StatementResponse)
async def my_personal_bill(
    db: AsyncSession = Depends(get_db), employee: Employee = Depends(get_current_employee)
) -> StatementResponse:
    service = LedgerService(db)
    account = await service.get_or_create_employee_account(employee.id)
    entries = await service.statement(
        account.id, source_types=[LedgerSourceType.PERSONAL_CONSUMPTION]
    )
    return _to_statement(entries)


@router.get("/me/private-guests", response_model=StatementResponse)
async def my_private_guest_bill(
    db: AsyncSession = Depends(get_db), employee: Employee = Depends(get_current_employee)
) -> StatementResponse:
    service = LedgerService(db)
    account = await service.get_or_create_employee_account(employee.id)
    entries = await service.statement(account.id, source_types=[LedgerSourceType.PRIVATE_GUEST])
    return _to_statement(entries)


@router.get("/me/consolidated", response_model=StatementResponse)
async def my_consolidated_bill(
    db: AsyncSession = Depends(get_db), employee: Employee = Depends(get_current_employee)
) -> StatementResponse:
    """"Consolidated personal + private guest view" (docs/billing.md) --
    still excludes OFFICIAL_GUEST, which never affects an employee's
    personal deduction."""
    service = LedgerService(db)
    account = await service.get_or_create_employee_account(employee.id)
    entries = await service.statement(
        account.id,
        source_types=[LedgerSourceType.PERSONAL_CONSUMPTION, LedgerSourceType.PRIVATE_GUEST],
    )
    return _to_statement(entries)


@router.get(
    "/official/{location_id}",
    response_model=StatementResponse,
)
async def official_guest_bill(
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(require_location_authority),
) -> StatementResponse:
    """"View official guest records where permitted" (requirements.md) --
    gated the same way as other location management actions."""
    service = LedgerService(db)
    account = await service.get_or_create_official_account(location_id)
    entries = await service.statement(account.id, source_types=[LedgerSourceType.OFFICIAL_GUEST])
    return _to_statement(entries)


@router.post(
    "/employees/{employee_id}/adjustments", response_model=LedgerEntryRead, status_code=201
)
async def adjust_employee_billing(
    employee_id: uuid.UUID,
    payload: EmployeeAdjustmentRequest,
    db: AsyncSession = Depends(get_db),
    admin: Employee = Depends(require_billing_admin),
) -> LedgerEntryRead:
    """"Adjust/reverse billing" (requirements.md, Management). Ad hoc,
    outside the served-quantity-correction flow -- e.g. a goodwill credit
    or fixing an error found during reconciliation."""
    if payload.source_type not in (
        LedgerSourceType.PERSONAL_CONSUMPTION,
        LedgerSourceType.PRIVATE_GUEST,
    ):
        raise ValidationAppError(
            "source_type must be PERSONAL_CONSUMPTION or PRIVATE_GUEST for an employee account"
        )

    service = LedgerService(db)
    account = await service.get_or_create_employee_account(employee_id)
    entry = await service.post_manual_adjustment(
        ledger_account_id=account.id,
        source_type=payload.source_type,
        entry_type=payload.entry_type,
        amount=payload.amount,
        reason=payload.reason,
        actor_id=admin.id,
        reversal_of_id=payload.reversal_of_id,
    )
    return LedgerEntryRead.model_validate(entry)


@router.post(
    "/official/{location_id}/adjustments", response_model=LedgerEntryRead, status_code=201
)
async def adjust_official_billing(
    location_id: uuid.UUID,
    payload: OfficialAdjustmentRequest,
    db: AsyncSession = Depends(get_db),
    manager: Employee = Depends(require_location_authority),
) -> LedgerEntryRead:
    service = LedgerService(db)
    account = await service.get_or_create_official_account(location_id)
    entry = await service.post_manual_adjustment(
        ledger_account_id=account.id,
        source_type=LedgerSourceType.OFFICIAL_GUEST,
        entry_type=payload.entry_type,
        amount=payload.amount,
        reason=payload.reason,
        actor_id=manager.id,
        reversal_of_id=payload.reversal_of_id,
    )
    return LedgerEntryRead.model_validate(entry)
