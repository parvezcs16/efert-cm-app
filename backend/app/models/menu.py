import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ActiveStatus, enum_column


class MenuCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Categories are location-scoped: each location curates and orders its
    own category list (see docs/database.md)."""

    __tablename__ = "menu_categories"
    __table_args__ = (
        UniqueConstraint("location_id", "name", name="uq_menu_category_location_name"),
    )

    location_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("locations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[ActiveStatus] = mapped_column(
        enum_column(ActiveStatus, "menu_category_status"),
        default=ActiveStatus.ACTIVE,
        nullable=False,
    )


class MenuItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The shared catalog entry for an item (name/description). Which
    locations actually sell it, at what price, is controlled by
    MenuItemLocation -- category assignment here is organizational and does
    not by itself restrict where the item can be sold."""

    __tablename__ = "menu_items"

    category_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("menu_categories.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    # Public URL path of the item's photo (e.g. /media/menu/<file>.jpg),
    # set via the image upload endpoint -- see app/services/media.
    image_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[ActiveStatus] = mapped_column(
        enum_column(ActiveStatus, "menu_item_status"), default=ActiveStatus.ACTIVE, nullable=False
    )


class MenuItemLocation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Per-location sellability: availability + internal price. This is the
    current/live state for ordering; OrderItem later snapshots the price at
    order time as the immutable historical record (see CLAUDE.md)."""

    __tablename__ = "menu_item_locations"
    __table_args__ = (
        UniqueConstraint("menu_item_id", "location_id", name="uq_menu_item_location"),
    )

    menu_item_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("menu_items.id"), nullable=False, index=True
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("locations.id"), nullable=False, index=True
    )
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
