import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ActiveStatus, enum_column


class Location(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "locations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    status: Mapped[ActiveStatus] = mapped_column(
        enum_column(ActiveStatus, "location_status"), default=ActiveStatus.ACTIVE, nullable=False
    )
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("employees.id")
    )


class KitchenStation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "kitchen_stations"

    location_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("locations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[ActiveStatus] = mapped_column(
        enum_column(ActiveStatus, "kitchen_station_status"),
        default=ActiveStatus.ACTIVE,
        nullable=False,
    )
