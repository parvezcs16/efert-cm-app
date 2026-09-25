from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import OtpPurpose
from app.models.otp import OtpChallenge


class OtpRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, challenge: OtpChallenge) -> None:
        self.db.add(challenge)

    async def flush(self) -> None:
        await self.db.flush()

    async def get_latest_active(self, subject: str, purpose: OtpPurpose) -> OtpChallenge | None:
        result = await self.db.execute(
            select(OtpChallenge)
            .where(
                OtpChallenge.subject == subject,
                OtpChallenge.purpose == purpose,
                OtpChallenge.consumed_at.is_(None),
                OtpChallenge.expires_at > datetime.now(UTC),
            )
            .order_by(OtpChallenge.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
