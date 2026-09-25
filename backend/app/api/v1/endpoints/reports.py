import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import SYSTEM_LEVEL_ROLES, require_location_authority, require_roles
from app.core.database import get_db
from app.models.employee import Employee
from app.schemas.report import (
    AuditLogRead,
    ReconciliationLineRead,
    ReconciliationResponse,
    SalesSummaryResponse,
)
from app.services.audit_service import AuditService
from app.services.reports.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])

_DEFAULT_LOOKBACK = timedelta(days=30)


def _resolve_period(
    since: datetime | None, until: datetime | None
) -> tuple[datetime, datetime]:
    resolved_until = until or datetime.now(UTC)
    resolved_since = since or (resolved_until - _DEFAULT_LOOKBACK)
    return resolved_since, resolved_until


@router.get("/locations/{location_id}/sales-summary", response_model=SalesSummaryResponse)
async def sales_summary(
    location_id: uuid.UUID,
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(require_location_authority),
) -> SalesSummaryResponse:
    resolved_since, resolved_until = _resolve_period(since, until)
    summary = await ReportService(db).sales_summary(
        location_id, since=resolved_since, until=resolved_until
    )
    return SalesSummaryResponse(
        location_id=location_id,
        since=resolved_since,
        until=resolved_until,
        total_orders=summary.total_orders,
        orders_by_status=summary.orders_by_status,
        orders_by_type=summary.orders_by_type,
        total_revenue=summary.total_revenue,
    )


@router.get("/locations/{location_id}/reconciliation", response_model=ReconciliationResponse)
async def reconciliation(
    location_id: uuid.UUID,
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(require_location_authority),
) -> ReconciliationResponse:
    resolved_since, resolved_until = _resolve_period(since, until)
    lines = await ReportService(db).reconciliation(
        location_id, since=resolved_since, until=resolved_until
    )
    reads = [
        ReconciliationLineRead(
            order_id=line.order_id,
            order_number=line.order_number,
            order_item_id=line.order_item_id,
            menu_item_id=line.menu_item_id,
            ordered_quantity=line.ordered_quantity,
            served_quantity=line.served_quantity,
            expected_amount=line.expected_amount,
            billed_amount=line.billed_amount,
            matches=line.matches,
        )
        for line in lines
    ]
    return ReconciliationResponse(
        location_id=location_id,
        since=resolved_since,
        until=resolved_until,
        lines=reads,
        mismatch_count=sum(1 for line in reads if not line.matches),
    )


@router.get("/audit-log", response_model=list[AuditLogRead])
async def audit_log(
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    actor_employee_id: uuid.UUID | None = Query(default=None),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(require_roles(*SYSTEM_LEVEL_ROLES)),
) -> list[AuditLogRead]:
    entries = await AuditService(db).search(
        entity_type=entity_type,
        entity_id=entity_id,
        actor_employee_id=actor_employee_id,
        since=since,
        until=until,
    )
    return [AuditLogRead.model_validate(e) for e in entries]
