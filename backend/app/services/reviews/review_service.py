import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.enums import OrderStatus, ReviewType
from app.models.review import Review, ReviewCategory, ReviewCategoryRating
from app.repositories.order_repository import OrderRepository
from app.repositories.review_repository import ReviewCategoryRepository, ReviewRepository
from app.services.audit_service import AuditService


class ReviewCategoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.categories = ReviewCategoryRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, *, location_id: uuid.UUID | None, name: str, created_by_id: uuid.UUID
    ) -> ReviewCategory:
        category = ReviewCategory(location_id=location_id, name=name, is_manager_defined=True)
        self.categories.add(category)
        await self.categories.flush()

        await self.audit.record(
            action="review_category.created",
            entity_type="review_category",
            entity_id=str(category.id),
            actor_employee_id=created_by_id,
            new_values={"location_id": str(location_id) if location_id else None, "name": name},
        )
        return category

    async def list_for_location(self, location_id: uuid.UUID) -> list[ReviewCategory]:
        return await self.categories.list_for_location(location_id)

    async def set_enabled(
        self, category_id: uuid.UUID, enabled: bool, actor_id: uuid.UUID
    ) -> ReviewCategory:
        category = await self.categories.get_by_id(category_id)
        if category is None:
            raise NotFoundError("Review category not found")

        category.enabled = enabled
        await self.categories.flush()

        await self.audit.record(
            action="review_category.enabled_changed",
            entity_type="review_category",
            entity_id=str(category.id),
            actor_employee_id=actor_id,
            new_values={"enabled": enabled},
        )
        return category


class ReviewService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.reviews = ReviewRepository(db)
        self.categories = ReviewCategoryRepository(db)
        self.orders = OrderRepository(db)
        self.audit = AuditService(db)

    async def submit(
        self,
        *,
        employee_id: uuid.UUID,
        location_id: uuid.UUID,
        review_type: ReviewType,
        order_id: uuid.UUID | None,
        is_anonymous: bool,
        overall_rating: int,
        comment: str | None,
        category_ratings: list[tuple[uuid.UUID, int]],
    ) -> Review:
        if not (1 <= overall_rating <= 5):
            raise ValidationAppError("overall_rating must be between 1 and 5")

        if review_type == ReviewType.ORDER:
            if order_id is None:
                raise ValidationAppError("order_id is required for an ORDER review")
            order = await self.orders.get_by_id(order_id)
            if order is None or order.employee_id != employee_id:
                raise NotFoundError("Order not found")
            if order.status != OrderStatus.SERVED:
                raise ValidationAppError("Only a served order can be reviewed")
            if order.location_id != location_id:
                raise ValidationAppError("location_id does not match the order's location")
        elif order_id is not None:
            raise ValidationAppError("order_id is only valid for an ORDER review")

        valid_categories = {c.id: c for c in await self.categories.list_for_location(location_id)}
        for category_id, rating in category_ratings:
            if category_id not in valid_categories:
                raise ValidationAppError(f"Category {category_id} is not available for review")
            if not (1 <= rating <= 5):
                raise ValidationAppError("Category ratings must be between 1 and 5")

        review = Review(
            location_id=location_id,
            employee_id=employee_id,
            is_anonymous=is_anonymous,
            review_type=review_type,
            order_id=order_id,
            overall_rating=overall_rating,
            comment=comment,
            category_ratings=[
                ReviewCategoryRating(category_id=category_id, rating=rating)
                for category_id, rating in category_ratings
            ],
        )
        self.reviews.add(review)
        await self.reviews.flush()

        await self.audit.record(
            action="review.submitted",
            entity_type="review",
            entity_id=str(review.id),
            actor_employee_id=employee_id,
            new_values={"review_type": review_type.value, "is_anonymous": is_anonymous},
        )
        return review

    async def list_for_location(self, location_id: uuid.UUID) -> list[Review]:
        return await self.reviews.list_for_location(location_id)

    async def list_for_employee(self, employee_id: uuid.UUID) -> list[Review]:
        return await self.reviews.list_for_employee(employee_id)
