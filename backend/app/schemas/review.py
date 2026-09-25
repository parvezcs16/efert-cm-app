import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import ReviewType


class ReviewCategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ReviewCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    location_id: uuid.UUID | None
    name: str
    enabled: bool
    is_manager_defined: bool


class ReviewCategoryRatingInput(BaseModel):
    category_id: uuid.UUID
    rating: int = Field(ge=1, le=5)


class ReviewSubmitRequest(BaseModel):
    location_id: uuid.UUID
    review_type: ReviewType
    order_id: uuid.UUID | None = None
    is_anonymous: bool = False
    overall_rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)
    category_ratings: list[ReviewCategoryRatingInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_order_id(self) -> "ReviewSubmitRequest":
        if self.review_type == ReviewType.ORDER and self.order_id is None:
            raise ValueError("order_id is required for an ORDER review")
        if self.review_type == ReviewType.OVERALL and self.order_id is not None:
            raise ValueError("order_id is only valid for an ORDER review")
        return self


class ReviewCategoryRatingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category_id: uuid.UUID
    rating: int


class ReviewRead(BaseModel):
    """Anonymity is enforced here, not just at submission time: employee_id
    is masked to null for any viewer whenever is_anonymous is set
    (docs/reviews.md "must not expose employee identity")."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    location_id: uuid.UUID
    employee_id: uuid.UUID | None
    is_anonymous: bool
    review_type: ReviewType
    order_id: uuid.UUID | None
    overall_rating: int
    comment: str | None
    created_at: datetime
    category_ratings: list[ReviewCategoryRatingRead]

    @model_validator(mode="after")
    def _mask_anonymous_identity(self) -> "ReviewRead":
        if self.is_anonymous:
            self.employee_id = None
        return self
