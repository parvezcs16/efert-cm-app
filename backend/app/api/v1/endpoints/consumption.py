import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_employee, require_kitchen_staff
from app.core.database import get_db
from app.models.employee import Employee
from app.schemas.consumption import (
    ConsumptionRecordRead,
    CorrectionRequestPayload,
    CorrectionValidatePayload,
)
from app.services.consumption.consumption_service import ConsumptionService

router = APIRouter(prefix="/orders/{order_id}/items/{item_id}/consumption", tags=["consumption"])


@router.get("", response_model=ConsumptionRecordRead)
async def get_consumption(
    order_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
) -> ConsumptionRecordRead:
    record = await ConsumptionService(db).get_for_order_item(order_id, item_id, employee.id)
    return ConsumptionRecordRead.model_validate(record)


@router.post("/request-correction", response_model=ConsumptionRecordRead)
async def request_correction(
    order_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: CorrectionRequestPayload,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
) -> ConsumptionRecordRead:
    record = await ConsumptionService(db).request_correction(
        order_id=order_id,
        order_item_id=item_id,
        employee_id=employee.id,
        requested_quantity=payload.requested_quantity,
        reason=payload.reason,
    )
    return ConsumptionRecordRead.model_validate(record)


@router.post("/validate-correction", response_model=ConsumptionRecordRead)
async def validate_correction(
    order_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: CorrectionValidatePayload,
    db: AsyncSession = Depends(get_db),
    staff: Employee = Depends(require_kitchen_staff),
) -> ConsumptionRecordRead:
    record = await ConsumptionService(db).validate_correction(
        order_id=order_id, order_item_id=item_id, actor_id=staff.id, approve=payload.approve
    )
    return ConsumptionRecordRead.model_validate(record)
