import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ActiveStatus


class MenuCategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    display_order: int = 0


class MenuCategoryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    display_order: int | None = None
    status: ActiveStatus | None = None


class MenuCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    location_id: uuid.UUID
    name: str
    display_order: int
    status: ActiveStatus


class MenuItemCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)


class MenuItemUpdateRequest(BaseModel):
    category_id: uuid.UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    status: ActiveStatus | None = None


class MenuItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_id: uuid.UUID
    name: str
    description: str | None
    image_url: str | None
    status: ActiveStatus


class MenuItemLocationUpsertRequest(BaseModel):
    is_available: bool = True
    price: Decimal = Field(gt=0, decimal_places=2)
    effective_from: datetime | None = None
    effective_to: datetime | None = None


class MenuItemLocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    menu_item_id: uuid.UUID
    location_id: uuid.UUID
    is_available: bool
    price: Decimal
    effective_from: datetime | None
    effective_to: datetime | None


class MenuPublishRequest(BaseModel):
    """The complete set of dishes to offer at a location. Everything else in
    the location's priced catalog is unpublished in the same transaction."""

    menu_item_ids: list[uuid.UUID] = Field(max_length=1000)


class MenuBrowseItem(BaseModel):
    """Employee-facing: no price, no internal availability-window details."""

    id: uuid.UUID
    name: str
    description: str | None
    image_url: str | None


class MenuBrowseCategory(BaseModel):
    id: uuid.UUID
    name: str
    display_order: int
    items: list[MenuBrowseItem]
