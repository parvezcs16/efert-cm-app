import hashlib
import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, NotFoundError, ValidationAppError
from app.core.security import GUEST_SESSION_TOKEN_VALIDITY
from app.models.enums import GuestSessionStatus, GuestType
from app.models.guest import Guest, GuestSession
from app.repositories.guest_repository import GuestRepository, GuestSessionRepository
from app.services.audit_service import AuditService


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class GuestService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.guests = GuestRepository(db)
        self.sessions = GuestSessionRepository(db)
        self.audit = AuditService(db)

    async def register(
        self,
        *,
        host_employee_id: uuid.UUID,
        name: str,
        company_name: str,
        cnic: str,
        guest_type: GuestType,
        accompanying_persons: int,
    ) -> Guest:
        guest = Guest(
            host_employee_id=host_employee_id,
            name=name,
            company_name=company_name,
            cnic=cnic,
            guest_type=guest_type,
            accompanying_persons=accompanying_persons,
        )
        self.guests.add(guest)
        await self.guests.flush()

        await self.audit.record(
            action="guest.registered",
            entity_type="guest",
            entity_id=str(guest.id),
            actor_employee_id=host_employee_id,
            new_values={"name": name, "guest_type": guest_type.value},
        )
        return guest

    async def get(self, guest_id: uuid.UUID) -> Guest:
        guest = await self.guests.get_by_id(guest_id)
        if guest is None:
            raise NotFoundError("Guest not found")
        return guest

    async def list_for_host(self, host_employee_id: uuid.UUID) -> list[Guest]:
        return await self.guests.list_for_host(host_employee_id)

    async def open_session(
        self, *, guest_id: uuid.UUID, host_employee_id: uuid.UUID
    ) -> tuple[GuestSession, str]:
        """Any active employee may open a new session for a previously
        registered guest, becoming that session's host -- not necessarily
        the same employee who originally registered the guest (docs:
        "a different employee brings the same previously-registered
        guest")."""
        await self.get(guest_id)

        raw_token = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        session = GuestSession(
            guest_id=guest_id,
            host_employee_id=host_employee_id,
            token_hash=_hash_token(raw_token),
            token_expires_at=now + GUEST_SESSION_TOKEN_VALIDITY,
            status=GuestSessionStatus.ACTIVE,
            opened_at=now,
        )
        self.sessions.add(session)
        await self.sessions.flush()

        await self.audit.record(
            action="guest_session.opened",
            entity_type="guest_session",
            entity_id=str(session.id),
            actor_employee_id=host_employee_id,
            new_values={"guest_id": str(guest_id)},
        )
        return session, raw_token

    async def list_sessions_for_guest(self, guest_id: uuid.UUID) -> list[GuestSession]:
        await self.get(guest_id)
        return await self.sessions.list_for_guest(guest_id)

    async def _get_owned_session(
        self, session_id: uuid.UUID, host_employee_id: uuid.UUID
    ) -> GuestSession:
        session = await self.sessions.get_by_id(session_id)
        if session is None or session.host_employee_id != host_employee_id:
            raise NotFoundError("Guest session not found")
        return session

    async def close_session(
        self, session_id: uuid.UUID, host_employee_id: uuid.UUID
    ) -> GuestSession:
        session = await self._get_owned_session(session_id, host_employee_id)
        if session.status != GuestSessionStatus.ACTIVE:
            raise ValidationAppError("Session is not active")

        session.status = GuestSessionStatus.CLOSED
        session.closed_at = datetime.now(UTC)
        await self.sessions.flush()

        await self.audit.record(
            action="guest_session.closed",
            entity_type="guest_session",
            entity_id=str(session.id),
            actor_employee_id=host_employee_id,
        )
        return session

    async def reopen_session(
        self, session_id: uuid.UUID, host_employee_id: uuid.UUID
    ) -> GuestSession:
        session = await self._get_owned_session(session_id, host_employee_id)
        if session.status != GuestSessionStatus.CLOSED:
            raise ValidationAppError("Session is not closed")
        if session.token_expires_at <= datetime.now(UTC):
            raise ValidationAppError("This session's QR token has expired and cannot be reopened")

        session.status = GuestSessionStatus.ACTIVE
        session.closed_at = None
        await self.sessions.flush()

        await self.audit.record(
            action="guest_session.reopened",
            entity_type="guest_session",
            entity_id=str(session.id),
            actor_employee_id=host_employee_id,
        )
        return session

    async def authenticate(self, raw_token: str) -> GuestSession:
        """Exchanges the raw QR token for the underlying session. Succeeds
        even if the session is CLOSED, as long as the 24h token window
        hasn't lapsed -- "QR access does not immediately become invalid on
        close" (CLAUDE.md). Callers that need the session to accept new
        activity (e.g. ordering) must check `session.status` themselves."""
        session = await self.sessions.get_by_token_hash(_hash_token(raw_token))
        if session is None or session.token_expires_at <= datetime.now(UTC):
            raise AuthenticationError("Invalid or expired guest token")
        return session
