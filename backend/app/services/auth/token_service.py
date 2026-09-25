import hashlib
import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError
from app.core.security import ACCESS_TOKEN_TTL, REFRESH_TOKEN_TTL, create_access_token
from app.models.employee import Employee
from app.models.token import RefreshToken
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.token_repository import RefreshTokenRepository


def _hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class TokenPair:
    def __init__(self, access_token: str, refresh_token: str, expires_in: int) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_in = expires_in


class TokenService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.tokens = RefreshTokenRepository(db)
        self.employees = EmployeeRepository(db)

    async def issue_pair(self, employee: Employee) -> TokenPair:
        access_token, _ = create_access_token(
            employee_id=employee.id,
            role=employee.role.value,
            password_state=employee.password_state.value,
        )

        raw_refresh = secrets.token_urlsafe(48)
        self.tokens.add(
            RefreshToken(
                employee_id=employee.id,
                token_hash=_hash_refresh_token(raw_refresh),
                expires_at=datetime.now(UTC) + REFRESH_TOKEN_TTL,
            )
        )
        await self.tokens.flush()

        return TokenPair(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=int(ACCESS_TOKEN_TTL.total_seconds()),
        )

    async def rotate(self, raw_refresh_token: str) -> TokenPair:
        token = await self.tokens.get_by_hash(_hash_refresh_token(raw_refresh_token))
        if token is None:
            raise AuthenticationError("Invalid refresh token")

        if token.revoked_at is not None:
            # Reuse of an already-rotated/revoked token is a signal of theft;
            # the safest response is to force re-authentication.
            raise AuthenticationError("Refresh token has already been used")

        if token.expires_at < datetime.now(UTC):
            raise AuthenticationError("Refresh token has expired")

        employee = await self.employees.get_by_id(token.employee_id)
        if employee is None:
            raise AuthenticationError("Invalid refresh token")

        new_pair = await self.issue_pair(employee)

        token.revoked_at = datetime.now(UTC)
        new_token = await self.tokens.get_by_hash(_hash_refresh_token(new_pair.refresh_token))
        if new_token is not None:
            token.replaced_by_id = new_token.id
        await self.tokens.flush()

        return new_pair

    async def revoke(self, raw_refresh_token: str) -> None:
        token = await self.tokens.get_by_hash(_hash_refresh_token(raw_refresh_token))
        if token is not None and token.revoked_at is None:
            token.revoked_at = datetime.now(UTC)
            await self.tokens.flush()

    async def get_employee_for_access_claims(self, employee_id: str) -> Employee | None:
        return await self.employees.get_by_id(uuid.UUID(employee_id))
