import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import GuestSessionStatus, GuestType, enum_column


class Guest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """`host_employee_id` here is who originally registered the guest;
    a given GuestSession can name a different host_employee_id if a
    different employee brings the same previously-registered guest on a
    later visit."""

    __tablename__ = "guests"

    host_employee_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    cnic: Mapped[str] = mapped_column(String(20), nullable=False)
    guest_type: Mapped[GuestType] = mapped_column(
        enum_column(GuestType, "guest_type"), nullable=False
    )
    accompanying_persons: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    sessions: Mapped[list["GuestSession"]] = relationship(back_populates="guest")


class GuestSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """`token_hash` follows the same opaque-bearer-token-plus-hash pattern
    as RefreshToken: the plaintext token is shown once (encoded in the QR)
    and never stored. `token_expires_at` is fixed at creation (the
    documented 24h rule) and is NOT extended or reset by closing the
    session -- closing only changes `status`."""

    __tablename__ = "guest_sessions"

    guest_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("guests.id"), nullable=False, index=True
    )
    host_employee_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[GuestSessionStatus] = mapped_column(
        enum_column(GuestSessionStatus, "guest_session_status"),
        default=GuestSessionStatus.ACTIVE,
        nullable=False,
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    guest: Mapped["Guest"] = relationship(back_populates="sessions")
