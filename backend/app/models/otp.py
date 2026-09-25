import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import OtpPurpose, enum_column


class OtpChallenge(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single OTP challenge. Only a keyed hash of the code is stored, never
    the plaintext code. `subject` is the p_no this challenge is issued for —
    it may precede the Employee row existing (e.g. during activation)."""

    __tablename__ = "otp_challenges"

    subject: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    purpose: Mapped[OtpPurpose] = mapped_column(
        enum_column(OtpPurpose, "otp_purpose"),
        nullable=False,
    )
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("employees.id")
    )

    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
