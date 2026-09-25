import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import (
    SYSTEM_LEVEL_ROLES,
    get_current_employee,
    require_location_authority,
    require_roles,
)
from app.core.database import get_db
from app.models.employee import Employee
from app.schemas.review import (
    ReviewCategoryCreateRequest,
    ReviewCategoryRead,
    ReviewRead,
    ReviewSubmitRequest,
)
from app.services.reviews.review_service import ReviewCategoryService, ReviewService

router = APIRouter(tags=["reviews"])


@router.post("/reviews", response_model=ReviewRead, status_code=201)
async def submit_review(
    payload: ReviewSubmitRequest,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
) -> ReviewRead:
    review = await ReviewService(db).submit(
        employee_id=employee.id,
        location_id=payload.location_id,
        review_type=payload.review_type,
        order_id=payload.order_id,
        is_anonymous=payload.is_anonymous,
        overall_rating=payload.overall_rating,
        comment=payload.comment,
        category_ratings=[(r.category_id, r.rating) for r in payload.category_ratings],
    )
    return ReviewRead.model_validate(review)


@router.get("/reviews/me", response_model=list[ReviewRead])
async def list_my_reviews(
    db: AsyncSession = Depends(get_db), employee: Employee = Depends(get_current_employee)
) -> list[ReviewRead]:
    reviews = await ReviewService(db).list_for_employee(employee.id)
    return [ReviewRead.model_validate(r) for r in reviews]


@router.get("/locations/{location_id}/reviews", response_model=list[ReviewRead])
async def list_location_reviews(
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(get_current_employee),
) -> list[ReviewRead]:
    reviews = await ReviewService(db).list_for_location(location_id)
    return [ReviewRead.model_validate(r) for r in reviews]


@router.get("/locations/{location_id}/review-categories", response_model=list[ReviewCategoryRead])
async def list_review_categories(
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(get_current_employee),
) -> list[ReviewCategoryRead]:
    categories = await ReviewCategoryService(db).list_for_location(location_id)
    return [ReviewCategoryRead.model_validate(c) for c in categories]


@router.post(
    "/locations/{location_id}/review-categories",
    response_model=ReviewCategoryRead,
    status_code=201,
)
async def create_location_review_category(
    location_id: uuid.UUID,
    payload: ReviewCategoryCreateRequest,
    db: AsyncSession = Depends(get_db),
    manager: Employee = Depends(require_location_authority),
) -> ReviewCategoryRead:
    category = await ReviewCategoryService(db).create(
        location_id=location_id, name=payload.name, created_by_id=manager.id
    )
    return ReviewCategoryRead.model_validate(category)


@router.post(
    "/review-categories/global", response_model=ReviewCategoryRead, status_code=201
)
async def create_global_review_category(
    payload: ReviewCategoryCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: Employee = Depends(require_roles(*SYSTEM_LEVEL_ROLES)),
) -> ReviewCategoryRead:
    category = await ReviewCategoryService(db).create(
        location_id=None, name=payload.name, created_by_id=admin.id
    )
    return ReviewCategoryRead.model_validate(category)


@router.patch("/review-categories/{category_id}/enabled", response_model=ReviewCategoryRead)
async def set_review_category_enabled(
    category_id: uuid.UUID,
    enabled: bool,
    db: AsyncSession = Depends(get_db),
    admin: Employee = Depends(require_roles(*SYSTEM_LEVEL_ROLES)),
) -> ReviewCategoryRead:
    category = await ReviewCategoryService(db).set_enabled(category_id, enabled, admin.id)
    return ReviewCategoryRead.model_validate(category)
