import uuid

import jwt
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import KITCHEN_STAFF_ROLES
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.enums import EmployeeStatus
from app.repositories.employee_repository import EmployeeRepository
from app.websocket.manager import kitchen_ws_manager

router = APIRouter()


async def _authenticate(websocket: WebSocket, db: AsyncSession) -> bool:
    """Browsers can't set an Authorization header on a WebSocket handshake,
    so the access token travels as a query param instead."""
    token = websocket.query_params.get("token")
    if not token:
        return False

    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        return False

    employee = await EmployeeRepository(db).get_by_id(uuid.UUID(payload["sub"]))
    return (
        employee is not None
        and employee.status == EmployeeStatus.ACTIVE
        and employee.role in KITCHEN_STAFF_ROLES
    )


@router.websocket("/ws/kitchen/{location_id}")
async def kitchen_feed(
    websocket: WebSocket, location_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> None:
    if not await _authenticate(websocket, db):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await kitchen_ws_manager.connect(location_id, websocket)
    try:
        while True:
            # Kitchen displays are read-only consumers; nothing meaningful
            # to do with client messages beyond keeping the socket alive.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        kitchen_ws_manager.disconnect(location_id, websocket)
