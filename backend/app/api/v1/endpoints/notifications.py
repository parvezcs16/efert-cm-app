import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_employee
from app.core.database import get_db
from app.models.employee import Employee
from app.schemas.notification import InAppNotificationRead, UnreadCountRead
from app.services.notifications.in_app_service import InAppNotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[InAppNotificationRead])
async def list_my_notifications(
    db: AsyncSession = Depends(get_db), employee: Employee = Depends(get_current_employee)
) -> list[InAppNotificationRead]:
    notifications = await InAppNotificationService(db).list_for_employee(employee.id)
    return [InAppNotificationRead.model_validate(n) for n in notifications]


@router.get("/unread-count", response_model=UnreadCountRead)
async def my_unread_count(
    db: AsyncSession = Depends(get_db), employee: Employee = Depends(get_current_employee)
) -> UnreadCountRead:
    return UnreadCountRead(unread=await InAppNotificationService(db).unread_count(employee.id))


@router.post("/{notification_id}/read", response_model=InAppNotificationRead)
async def mark_notification_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
) -> InAppNotificationRead:
    notification = await InAppNotificationService(db).mark_read(notification_id, employee.id)
    return InAppNotificationRead.model_validate(notification)


@router.post("/read-all", status_code=204)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db), employee: Employee = Depends(get_current_employee)
) -> None:
    await InAppNotificationService(db).mark_all_read(employee.id)
