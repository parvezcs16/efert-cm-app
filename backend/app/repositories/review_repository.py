import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.review import Review, ReviewCategory


class ReviewCategoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, category_id: uuid.UUID) -> ReviewCategory | None:
        return await self.db.get(ReviewCategory, category_id)

    async def list_for_location(self, location_id: uuid.UUID) -> list[ReviewCategory]:
        """Global (system-defined) categories plus this location's own."""
        result = await self.db.execute(
            select(ReviewCategory)
            .where(
                ReviewCategory.enabled.is_(True),
                (ReviewCategory.location_id.is_(None))
                | (ReviewCategory.location_id == location_id),
            )
            .order_by(ReviewCategory.name)
        )
        return list(result.scalars().all())

    def add(self, category: ReviewCategory) -> None:
        self.db.add(category)

    async def flush(self) -> None:
        await self.db.flush()


class ReviewRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, review_id: uuid.UUID) -> Review | None:
        result = await self.db.execute(
            select(Review)
            .where(Review.id == review_id)
            .options(selectinload(Review.category_ratings))
        )
        return result.scalar_one_or_none()

    async def list_for_location(self, location_id: uuid.UUID) -> list[Review]:
        result = await self.db.execute(
            select(Review)
            .where(Review.location_id == location_id)
            .options(selectinload(Review.category_ratings))
            .order_by(Review.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_for_employee(self, employee_id: uuid.UUID) -> list[Review]:
        result = await self.db.execute(
            select(Review)
            .where(Review.employee_id == employee_id)
            .options(selectinload(Review.category_ratings))
            .order_by(Review.created_at.desc())
        )
        return list(result.scalars().all())

    def add(self, review: Review) -> None:
        self.db.add(review)

    async def flush(self) -> None:
        await self.db.flush()
