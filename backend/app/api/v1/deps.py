import uuid
from collections.abc import Callable

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_access_token, decode_guest_access_token
from app.models.employee import Employee
from app.models.enums import EmployeeRole, EmployeeStatus, GuestSessionStatus
from app.models.guest import GuestSession
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.guest_repository import GuestSessionRepository
from app.repositories.location_repository import LocationRepository

SYSTEM_LEVEL_ROLES = (EmployeeRole.SYSTEM_MANAGER, EmployeeRole.SYSTEM_ADMINISTRATOR)

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_employee(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Employee:
    if credentials is None:
        raise AuthenticationError("Missing bearer token")

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired token") from exc

    employee = await EmployeeRepository(db).get_by_id(uuid.UUID(payload["sub"]))
    if employee is None or employee.status != EmployeeStatus.ACTIVE:
        raise AuthenticationError("Account is not active")

    # Defense in depth: a still-valid access token issued before a forced
    # password reset should not grant access to protected business routes.
    if employee.password_state.value != "OK":
        raise AuthorizationError("Password change required before continuing")

    return employee


def require_roles(*roles: EmployeeRole) -> Callable:
    async def _dependency(employee: Employee = Depends(get_current_employee)) -> Employee:
        if employee.role not in roles:
            raise AuthorizationError("You do not have permission to perform this action")
        return employee

    return _dependency


KITCHEN_STAFF_ROLES = (
    EmployeeRole.SERVER,
    EmployeeRole.KITCHEN_OPERATOR,
    EmployeeRole.LOCATION_MANAGER,
    *SYSTEM_LEVEL_ROLES,
)

# Kitchen/server operations are role-gated only, not location-scoped: the
# Employee model (Phase 2) has no "home location" for SERVER/KITCHEN_OPERATOR
# staff to check against (only Location.manager_id ties one employee to one
# location). See docs/implementation-notes.md Phase 5 for the trade-off.
require_kitchen_staff = require_roles(*KITCHEN_STAFF_ROLES)

BILLING_ADMIN_ROLES = (EmployeeRole.FINANCE_ADMIN, *SYSTEM_LEVEL_ROLES)
require_billing_admin = require_roles(*BILLING_ADMIN_ROLES)


async def require_location_authority(
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
) -> Employee:
    """Allows system-level roles unconditionally, and a LOCATION_MANAGER
    only for the specific location they are assigned to manage."""
    if employee.role in SYSTEM_LEVEL_ROLES:
        return employee

    if employee.role == EmployeeRole.LOCATION_MANAGER:
        location = await LocationRepository(db).get_by_id(location_id)
        if location is not None and location.manager_id == employee.id:
            return employee

    raise AuthorizationError("You do not have permission to manage this location")


async def get_current_guest_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> GuestSession:
    if credentials is None:
        raise AuthenticationError("Missing bearer token")

    try:
        session_id = decode_guest_access_token(credentials.credentials)
    except ValueError as exc:
        raise AuthenticationError(str(exc)) from exc

    session = await GuestSessionRepository(db).get_by_id(session_id)
    if session is None:
        raise AuthenticationError("Guest session not found")

    # The JWT only proves "this is session X"; ACTIVE is re-checked live so
    # a host closing the session mid-visit takes effect immediately, even
    # against an already-issued, still-unexpired access token.
    if session.status != GuestSessionStatus.ACTIVE:
        raise AuthorizationError("This guest session is closed")

    return session
