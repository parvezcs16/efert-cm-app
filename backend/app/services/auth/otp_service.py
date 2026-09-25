import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import RateLimitedError, ValidationAppError
from app.models.enums import OtpPurpose
from app.models.otp import OtpChallenge
from app.repositories.otp_repository import OtpRepository
from app.services.audit_service import AuditService

settings = get_settings()


def _hash_code(code: str, subject: str, purpose: OtpPurpose) -> str:
    # Subject + purpose are mixed into the HMAC so a leaked hash cannot be
    # replayed against a different subject/purpose pair.
    message = f"{subject}:{purpose.value}:{code}".encode()
    return hmac.new(settings.secret_key.encode(), message, hashlib.sha256).hexdigest()


class OtpService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = OtpRepository(db)
        self.audit = AuditService(db)

    async def issue(
        self, *, subject: str, purpose: OtpPurpose, employee_id: uuid.UUID | None = None
    ) -> str:
        """Create a new OTP challenge and return the plaintext code to send.
        Raises RateLimitedError if a resend is requested too soon."""
        existing = await self.repo.get_latest_active(subject, purpose)
        if existing is not None:
            age = datetime.now(UTC) - existing.created_at
            cooldown = timedelta(seconds=settings.otp_resend_cooldown_seconds)
            if age < cooldown:
                wait_seconds = int((cooldown - age).total_seconds())
                raise RateLimitedError(
                    f"Please wait {wait_seconds}s before requesting another code"
                )

        code = f"{secrets.randbelow(1_000_000):06d}"
        challenge = OtpChallenge(
            subject=subject,
            purpose=purpose,
            employee_id=employee_id,
            code_hash=_hash_code(code, subject, purpose),
            expires_at=datetime.now(UTC) + timedelta(seconds=settings.otp_ttl_seconds),
            max_attempts=settings.otp_max_attempts,
        )
        self.repo.add(challenge)
        await self.repo.flush()

        await self.audit.record(
            action="otp.issued",
            entity_type="otp_challenge",
            entity_id=str(challenge.id),
            actor_employee_id=employee_id,
            new_values={"subject": subject, "purpose": purpose.value},
        )
        return code

    async def verify(self, *, subject: str, purpose: OtpPurpose, code: str) -> None:
        """Verify a code against the latest active challenge. Raises
        ValidationAppError on mismatch/expiry/exhaustion; consumes the
        challenge on success so it cannot be reused."""
        challenge = await self.repo.get_latest_active(subject, purpose)
        if challenge is None:
            raise ValidationAppError("No active verification code for this request")

        if challenge.attempts >= challenge.max_attempts:
            raise ValidationAppError("Too many incorrect attempts; request a new code")

        expected_hash = _hash_code(code, subject, purpose)
        if not hmac.compare_digest(expected_hash, challenge.code_hash):
            challenge.attempts += 1
            await self.repo.flush()
            await self.audit.record(
                action="otp.verify_failed",
                entity_type="otp_challenge",
                entity_id=str(challenge.id),
                new_values={"subject": subject, "purpose": purpose.value},
            )
            raise ValidationAppError("Incorrect verification code")

        challenge.consumed_at = datetime.now(UTC)
        await self.repo.flush()
        await self.audit.record(
            action="otp.verified",
            entity_type="otp_challenge",
            entity_id=str(challenge.id),
            new_values={"subject": subject, "purpose": purpose.value},
        )
