import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ReviewType, enum_column

# The canonical seed list (docs/reviews.md "Initial categories"). The
# migration that creates review_categories inserts these directly (kept
# self-contained/frozen, as migrations should be); this constant exists so
# non-migration code -- e.g. the test suite's schema setup, which uses
# Base.metadata.create_all instead of running migrations -- can seed the
# same defaults without duplicating the literal list.
DEFAULT_REVIEW_CATEGORIES = ("Food", "Environment", "Hygiene", "Server Behavior")


class ReviewCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """`location_id` null = system-defined, global category (the four
    seeded defaults: FOOD/ENVIRONMENT/HYGIENE/SERVER_BEHAVIOR); set =
    manager-defined, local to that location (docs/reviews.md
    "Configuration"). Names are never edited in place once created --
    disable and add a new one instead -- so a historical
    ReviewCategoryRating stays interpretable via a stable FK
    (docs/reviews.md "keep review configuration versioned enough")."""

    __tablename__ = "review_categories"

    location_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("locations.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_manager_defined: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Review(UUIDPrimaryKeyMixin, Base):
    """No TimestampMixin: a review is never edited after submission, only
    created_at is meaningful. `employee_id` is retained even when
    `is_anonymous` (needed for e.g. duplicate/abuse handling), but
    ReviewRead always nulls it out -- "anonymous reviews must not expose
    employee identity through normal management review screens"
    (docs/reviews.md)."""

    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint(
            "(review_type = 'ORDER' AND order_id IS NOT NULL)"
            " OR (review_type = 'OVERALL' AND order_id IS NULL)",
            name="ck_review_order_id_matches_type",
        ),
        CheckConstraint("overall_rating BETWEEN 1 AND 5", name="ck_review_rating_range"),
    )

    location_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("locations.id"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True
    )
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    review_type: Mapped[ReviewType] = mapped_column(
        enum_column(ReviewType, "review_type"), nullable=False
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("orders.id")
    )
    overall_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    category_ratings: Mapped[list["ReviewCategoryRating"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )


class ReviewCategoryRating(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "review_category_ratings"
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="ck_category_rating_range"),)

    review_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False, index=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("review_categories.id"), nullable=False
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)

    review: Mapped["Review"] = relationship(back_populates="category_ratings")
