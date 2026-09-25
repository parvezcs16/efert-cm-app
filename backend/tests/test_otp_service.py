from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import RateLimitedError, ValidationAppError
from app.models.enums import OtpPurpose
from app.services.auth.otp_service import OtpService

settings = get_settings()


async def test_otp_verify_succeeds_with_correct_code(db_session: AsyncSession) -> None:
    service = OtpService(db_session)
    code = await service.issue(subject="P1", purpose=OtpPurpose.ACTIVATION)
    await service.verify(subject="P1", purpose=OtpPurpose.ACTIVATION, code=code)


async def test_otp_verify_fails_with_wrong_code(db_session: AsyncSession) -> None:
    service = OtpService(db_session)
    await service.issue(subject="P2", purpose=OtpPurpose.ACTIVATION)
    with pytest.raises(ValidationAppError):
        await service.verify(subject="P2", purpose=OtpPurpose.ACTIVATION, code="000000")


async def test_otp_locks_out_after_max_attempts(db_session: AsyncSession) -> None:
    service = OtpService(db_session)
    code = await service.issue(subject="P3", purpose=OtpPurpose.ACTIVATION)

    for _ in range(settings.otp_max_attempts):
        with pytest.raises(ValidationAppError):
            await service.verify(subject="P3", purpose=OtpPurpose.ACTIVATION, code="000000")

    # Even the correct code is now rejected; a new OTP must be requested.
    with pytest.raises(ValidationAppError, match="Too many incorrect attempts"):
        await service.verify(subject="P3", purpose=OtpPurpose.ACTIVATION, code=code)


async def test_otp_expires(db_session: AsyncSession) -> None:
    service = OtpService(db_session)
    code = await service.issue(subject="P4", purpose=OtpPurpose.ACTIVATION)

    challenge = await service.repo.get_latest_active("P4", OtpPurpose.ACTIVATION)
    assert challenge is not None
    challenge.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.flush()

    with pytest.raises(ValidationAppError, match="No active verification code"):
        await service.verify(subject="P4", purpose=OtpPurpose.ACTIVATION, code=code)


async def test_otp_resend_before_cooldown_is_rate_limited(db_session: AsyncSession) -> None:
    service = OtpService(db_session)
    await service.issue(subject="P5", purpose=OtpPurpose.ACTIVATION)

    with pytest.raises(RateLimitedError):
        await service.issue(subject="P5", purpose=OtpPurpose.ACTIVATION)


async def test_otp_is_scoped_to_purpose(db_session: AsyncSession) -> None:
    service = OtpService(db_session)
    code = await service.issue(subject="P6", purpose=OtpPurpose.ACTIVATION)

    with pytest.raises(ValidationAppError):
        await service.verify(subject="P6", purpose=OtpPurpose.PASSWORD_RESET, code=code)
